using Printf, TOML

format_num(x) = @sprintf("%.6f", isapprox(x, 0.0; atol=1e-9) ? 0.0 : x)

required_key(table, key, context) = haskey(table, key) ? table[key] : error("Missing `$(key)` in $(context)")

function resolve_repo_path(path)
    return isabspath(path) ? path : normpath(joinpath(@__DIR__, path))
end

function read_load_profile(path)
    load = Float64[]
    datetimes = String[]

    open(path) do io
        readline(io)
        for line in eachline(io)
            parts = split(line, ",")
            length(parts) >= 3 || error("Expected at least 3 columns in $(path)")
            push!(load, parse(Float64, parts[2]))
            push!(datetimes, strip(parts[3]))
        end
    end

    isempty(load) && error("Load profile $(path) is empty")
    return load, datetimes
end

function load_model_config(config_path)
    raw = TOML.parsefile(config_path)

    run_cfg = get(raw, "run", Dict{String, Any}())
    scheduling_cfg = required_key(raw, "scheduling", config_path)
    load_profile_cfg = required_key(raw, "load_profile", config_path)
    battery_cfg = required_key(raw, "battery", config_path)
    initial_cfg = required_key(raw, "initial_conditions", config_path)
    generator_cfgs = required_key(raw, "generators", config_path)

    dt_minutes = Int(required_key(scheduling_cfg, "dt_minutes", "[scheduling]"))
    dt = dt_minutes / 60.0

    load_profile_path = resolve_repo_path(String(required_key(load_profile_cfg, "path", "[load_profile]")))

    gensets = [
        (
            P_max = Float64(required_key(g, "P_max", "[[generators]]")),
            P_min = Float64(required_key(g, "P_min", "[[generators]]")),
            P = Float64.(required_key(g, "P", "[[generators]]")),
            SFOC = Float64.(required_key(g, "SFOC", "[[generators]]")),
            startup_cost = Float64(required_key(g, "startup_cost", "[[generators]]")),
        )
        for g in generator_cfgs
    ]

    initial_commitment = Int.(required_key(initial_cfg, "generator_commitment", "[initial_conditions]"))
    length(initial_commitment) == length(gensets) || error(
        "Configured generator_commitment length ($(length(initial_commitment))) does not match number of generators ($(length(gensets)))."
    )

    battery = (
        E_max     = Float64(required_key(battery_cfg, "E_max", "[battery]")),
        SOC_min   = Float64(required_key(battery_cfg, "SOC_min", "[battery]")),
        SOC_max   = Float64(required_key(battery_cfg, "SOC_max", "[battery]")),
        P_ch_max  = Float64(required_key(battery_cfg, "P_ch_max", "[battery]")),
        P_dis_max = Float64(required_key(battery_cfg, "P_dis_max", "[battery]")),
        eta_ch    = Float64(required_key(battery_cfg, "eta_ch", "[battery]")),
        eta_dis   = Float64(required_key(battery_cfg, "eta_dis", "[battery]")),
        E_init    = Float64(required_key(initial_cfg, "battery_energy_kwh", "[initial_conditions]")),
        E_terminal_min = begin
            terminal_cfg = get(raw, "terminal_conditions", Dict{String, Any}())
            if haskey(terminal_cfg, "battery_energy_min_kwh")
                Float64(terminal_cfg["battery_energy_min_kwh"])
            else
                Float64(required_key(initial_cfg, "battery_energy_kwh", "[initial_conditions]"))
            end
        end,
        dt        = dt,
    )

    return (
        run_label = String(get(run_cfg, "label", "")),
        run_desc = String(get(run_cfg, "description", "")),
        show_solver_log = Bool(get(run_cfg, "show_solver_log", true)),
        config_path = config_path,
        load_profile_path = load_profile_path,
        dt_minutes = dt_minutes,
        gensets = gensets,
        battery = battery,
        initial_commitment = initial_commitment,
    )
end

function battery_energy_metadata(battery)
    return Dict(
        "E_cap"    => battery.E_max,
        "E_min"    => battery.SOC_min * battery.E_max,
        "E_max"    => battery.SOC_max * battery.E_max,
        "E_init"   => battery.E_init,
        "E_terminal_min" => battery.E_terminal_min,
        "SOC_min"  => battery.SOC_min,
        "SOC_max"  => battery.SOC_max,
        "SOC_terminal_min" => battery.E_terminal_min / battery.E_max,
        "P_ch_max" => battery.P_ch_max,
        "P_dis_max"=> battery.P_dis_max,
        "eta_ch"   => battery.eta_ch,
        "eta_dis"  => battery.eta_dis,
        "dt"       => battery.dt,
    )
end

function validation_metadata(load, datetimes, battery, Pg, P_ch, P_dis, E; primal_tolerance=1e-6, mip_tolerance=0.0, energy_tolerance=1e-6)
    T = eachindex(load)
    G = axes(Pg, 1)

    max_power_abs_residual = -1.0
    max_power_residual = 0.0
    max_power_step = first(T)
    for t in T
        residual = sum(Pg[g, t] for g in G) + P_dis[t] - P_ch[t] - load[t]
        abs_residual = abs(residual)
        if abs_residual > max_power_abs_residual
            max_power_abs_residual = abs_residual
            max_power_residual = residual
            max_power_step = t
        end
    end

    initial_energy_residual = E[first(T)] - battery.E_init
    max_energy_abs_residual = -1.0
    max_energy_residual = 0.0
    max_energy_step = first(T)
    for t in T
        residual = E[t + 1] - (
            E[t] + battery.dt * (
                battery.eta_ch * P_ch[t] -
                (1.0 / battery.eta_dis) * P_dis[t]
            )
        )
        abs_residual = abs(residual)
        if abs_residual > max_energy_abs_residual
            max_energy_abs_residual = abs_residual
            max_energy_residual = residual
            max_energy_step = t
        end
    end

    terminal_energy = E[length(load) + 1]
    terminal_soc = terminal_energy / battery.E_max

    return Dict(
        "solver_tolerances" => Dict(
            "primal_feasibility" => primal_tolerance,
            "mip_feasibility" => mip_tolerance,
            "energy_residual_tolerance_kwh" => energy_tolerance,
        ),
        "power_balance" => Dict(
            "max_abs_residual_kw" => max_power_abs_residual,
            "max_residual_kw" => max_power_residual,
            "max_residual_timestep" => max_power_step,
            "max_residual_datetime" => datetimes[max_power_step],
            "within_primal_feasibility_tolerance" => max_power_abs_residual <= primal_tolerance,
        ),
        "battery_energy" => Dict(
            "initial_residual_kwh" => initial_energy_residual,
            "max_abs_dynamic_residual_kwh" => max_energy_abs_residual,
            "max_dynamic_residual_kwh" => max_energy_residual,
            "max_dynamic_residual_from_timestep" => max_energy_step,
            "max_dynamic_residual_from_datetime" => datetimes[max_energy_step],
            "max_dynamic_residual_to_timestep" => max_energy_step + 1,
            "terminal_energy_kwh" => terminal_energy,
            "terminal_soc_pct" => terminal_soc * 100.0,
            "terminal_target_min_kwh" => battery.E_terminal_min,
            "terminal_target_min_soc_pct" => battery.E_terminal_min / battery.E_max * 100.0,
            "terminal_constraint_residual_kwh" => terminal_energy - battery.E_terminal_min,
            "within_primal_feasibility_tolerance" => (
                abs(initial_energy_residual) <= energy_tolerance &&
                max_energy_abs_residual <= energy_tolerance
            ),
        ),
    )
end

function generator_operating_point(genset, pg)
    n = length(genset.P)
    lambdas = zeros(Float64, n)

    if isapprox(pg, 0.0; atol=1e-9)
        return 0.0, 0.0, lambdas
    end

    (pg >= first(genset.P) - 1e-9 && pg <= last(genset.P) + 1e-9) || error(
        "Generator power $(pg) kW lies outside the modeled breakpoint range $(first(genset.P)) - $(last(genset.P)) kW."
    )

    for i in eachindex(genset.P)
        if isapprox(pg, genset.P[i]; atol=1e-9)
            lambdas[i] = 1.0
            sfoc = genset.SFOC[i]
            return sfoc, pg * sfoc, lambdas
        end
    end

    for i in 1:(n - 1)
        p_lo = genset.P[i]
        p_hi = genset.P[i + 1]
        if p_lo <= pg <= p_hi
            alpha = (pg - p_lo) / (p_hi - p_lo)
            lambdas[i] = 1.0 - alpha
            lambdas[i + 1] = alpha
            sfoc = sum(lambdas[j] * genset.SFOC[j] for j in eachindex(lambdas))
            mdot = sum(lambdas[j] * genset.P[j] * genset.SFOC[j] for j in eachindex(lambdas))
            return sfoc, mdot, lambdas
        end
    end

    error("Failed to interpolate generator power $(pg) kW against the configured breakpoints.")
end

function preferred_generator_power(genset)
    min_sfoc = minimum(genset.SFOC)
    preferred_candidates = [
        genset.P[i] for i in eachindex(genset.SFOC)
        if isapprox(genset.SFOC[i], min_sfoc; atol=1e-9)
    ]
    return maximum(preferred_candidates)
end

# Exported SFOC should reflect the realized fuel-flow relation, i.e. mdot / Pg.
function exported_sfoc_gkwh(results, g, t)
    pg_val = results.Pg[g, t]
    isapprox(pg_val, 0.0; atol=1e-9) && return 0.0

    if hasproperty(results, :mdot)
        return results.mdot[g, t] / pg_val
    end
    if hasproperty(results, :SFOC)
        return results.SFOC[g, t]
    end

    error("Results are missing both `mdot` and `SFOC` needed for `sfoc_gkwh` export.")
end

function write_results_csv(path, load, datetimes, gensets, battery, results)
    max_breakpoints = maximum(length(g.SFOC) for g in gensets)

    open(path, "w") do io
        header = ["timestep", "datetime", "generator", "load_kw", "u", "startup",
                  "Pg_kw", "sfoc_gkwh", "fuel_gph", "load_pct",
                  "P_ch_kw", "P_dis_kw", "E_kwh", "soc_pct"]
        append!(header, ["lambda_$(i)" for i in 1:max_breakpoints])
        println(io, join(header, ","))

        for t in eachindex(load), g in eachindex(gensets)
            pg_val = isapprox(results.Pg[g, t], 0.0; atol=1e-9) ? 0.0 : results.Pg[g, t]
            sfoc_raw = exported_sfoc_gkwh(results, g, t)
            sfoc_val = isapprox(sfoc_raw, 0.0; atol=1e-9) ? 0.0 : sfoc_raw
            fuel_val = isapprox(results.mdot[g, t], 0.0; atol=1e-9) ? 0.0 : results.mdot[g, t]
            loadpct = pg_val / gensets[g].P_max * 100.0

            pch_val = isapprox(results.P_ch[t], 0.0; atol=1e-9) ? 0.0 : results.P_ch[t]
            pdis_val = isapprox(results.P_dis[t], 0.0; atol=1e-9) ? 0.0 : results.P_dis[t]
            e_val = results.E[t]
            soc_val = e_val / battery.E_max * 100.0

            row = [
                string(t),
                datetimes[t],
                string(g),
                @sprintf("%.1f", load[t]),
                results.u[g, t] > 0.5 ? "1" : "0",
                results.y[g, t] > 0.5 ? "1" : "0",
                format_num(pg_val),
                format_num(sfoc_val),
                format_num(fuel_val),
                @sprintf("%.2f", loadpct),
                format_num(pch_val),
                format_num(pdis_val),
                format_num(e_val),
                @sprintf("%.2f", soc_val),
            ]

            for i in 1:max_breakpoints
                if i <= size(results.lambda, 3)
                    push!(row, format_num(results.lambda[g, t, i]))
                else
                    push!(row, "")
                end
            end

            println(io, join(row, ","))
        end
    end
end
