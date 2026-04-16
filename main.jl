using JuMP, HiGHS, Printf, Dates, TOML

include("model.jl")

format_num(x) = @sprintf("%.6f", isapprox(x, 0.0; atol=1e-9) ? 0.0 : x)

function write_results_csv(path, load, datetimes, gensets, battery, u, y, Pg, SFOC, mdot, lambda, P_ch, P_dis, E)
    max_breakpoints = maximum(length(g.SFOC) for g in gensets)

    open(path, "w") do io
        header = ["timestep", "datetime", "generator", "load_kw", "u", "startup",
                  "Pg_kw", "sfoc_gkwh", "fuel_gph", "load_pct",
                  "P_ch_kw", "P_dis_kw", "E_kwh", "soc_pct"]
        append!(header, ["lambda_$(i)" for i in 1:max_breakpoints])
        println(io, join(header, ","))

        for t in eachindex(load), g in eachindex(gensets)
            pg_val  = value(Pg[g, t])
            fg_val  = value(SFOC[g, t])
            fuel_val = value(mdot[g, t])
            pg_val  = isapprox(pg_val, 0.0; atol=1e-9) ? 0.0 : pg_val
            fg_val  = isapprox(fg_val, 0.0; atol=1e-9) ? 0.0 : fg_val
            fuel_val = isapprox(fuel_val, 0.0; atol=1e-9) ? 0.0 : fuel_val
            loadpct = pg_val / gensets[g].P_max * 100.0

            pch_val  = isapprox(value(P_ch[t]), 0.0; atol=1e-9) ? 0.0 : value(P_ch[t])
            pdis_val = isapprox(value(P_dis[t]), 0.0; atol=1e-9) ? 0.0 : value(P_dis[t])
            e_val    = value(E[t])
            soc_val  = e_val / battery.E_max * 100.0

            row = [
                string(t),
                datetimes[t],
                string(g),
                @sprintf("%.1f", load[t]),
                value(u[g, t]) > 0.5 ? "1" : "0",
                value(y[g, t]) > 0.5 ? "1" : "0",
                format_num(pg_val),
                format_num(fg_val),
                format_num(fuel_val),
                @sprintf("%.2f", loadpct),
                format_num(pch_val),
                format_num(pdis_val),
                format_num(e_val),
                @sprintf("%.2f", soc_val),
            ]

            for i in 1:max_breakpoints
                if i <= length(gensets[g].SFOC)
                    push!(row, format_num(value(lambda[g, t, i])))
                else
                    push!(row, "")
                end
            end

            println(io, join(row, ","))
        end
    end
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

required_key(table, key, context) = haskey(table, key) ? table[key] : error("Missing `$(key)` in $(context)")

function resolve_repo_path(path)
    return isabspath(path) ? path : normpath(joinpath(@__DIR__, path))
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

function main()
    config_arg = isempty(ARGS) ? joinpath("config", "baseline_model.toml") : ARGS[1]
    config_path = resolve_repo_path(config_arg)
    cfg = load_model_config(config_path)

    run_label = cfg.run_label
    run_desc  = cfg.run_desc
    git_hash  = strip(read(`git rev-parse HEAD`, String))
    git_dirty = !success(`git diff --quiet HEAD`)

    gensets = cfg.gensets
    battery = cfg.battery
    dt_minutes = cfg.dt_minutes
    load_profile_path = cfg.load_profile_path
    isfile(load_profile_path) || error(
        "Missing $(load_profile_path) referenced by $(config_path)."
    )
    load, datetimes = read_load_profile(load_profile_path)

    show_solver_log = cfg.show_solver_log

    model, u, y, Pg, SFOC, mdot, lambda, P_ch, P_dis, E = build_model(gensets, load, battery, cfg.initial_commitment)

    if !show_solver_log
        set_silent(model)
    end

    optimize!(model)

    if termination_status(model) == OPTIMAL
        timestamp = Dates.format(now(), "yyyy-mm-dd_HHMMSS")
        run_dir = joinpath(@__DIR__, "runs", "$(timestamp)_$(run_label)")
        mkpath(run_dir)

        params_dict = Dict(
            "run" => Dict(
                "date"        => Dates.format(now(), "yyyy-mm-dd"),
                "label"       => run_label,
                "description" => run_desc,
                "git_hash"    => git_hash,
                "git_dirty"   => git_dirty,
                "config_file" => config_path,
            ),
            "solver" => Dict(
                "status"       => string(termination_status(model)),
                "objective"    => objective_value(model),
                "solve_time_s" => solve_time(model),
            ),
            "battery" => Dict(
                "E_max"       => battery.E_max,
                "SOC_min"     => battery.SOC_min,
                "SOC_max"     => battery.SOC_max,
                "P_ch_max"    => battery.P_ch_max,
                "P_dis_max"   => battery.P_dis_max,
                "eta_ch"      => battery.eta_ch,
                "eta_dis"     => battery.eta_dis,
                "E_init"      => battery.E_init,
                "dt"          => battery.dt,
            ),
            "initial_conditions" => Dict(
                "generator_commitment" => collect(cfg.initial_commitment),
                "battery_energy_kwh"   => battery.E_init,
            ),
            "load_profile" => Dict(
                "source_file"     => load_profile_path,
                "timesteps"       => length(load),
                "start_datetime"  => datetimes[1],
                "end_datetime"    => datetimes[end],
                "dt_minutes"      => dt_minutes,
            ),
            "generators" => [
                Dict(
                    "P_max"        => g.P_max,
                    "P_min"        => g.P_min,
                    "P"            => collect(Float64, g.P),
                    "SFOC"         => collect(Float64, g.SFOC),
                    "startup_cost" => g.startup_cost,
                )
                for g in gensets
            ],
        )
        open(joinpath(run_dir, "params.toml"), "w") do io
            TOML.print(io, params_dict)
        end

        csv_path = joinpath(run_dir, "dispatch_results.csv")
        write_results_csv(csv_path, load, datetimes, gensets, battery, u, y, Pg, SFOC, mdot, lambda, P_ch, P_dis, E)

        open(joinpath(@__DIR__, ".current_run"), "w") do io
            write(io, run_dir)
        end

        println("Objective value = ", @sprintf("%.2f", objective_value(model)))
        println("Solve time      = ", @sprintf("%.2f", solve_time(model)), " s")
        println("Run saved to    -> ", run_dir)
    else
        println("Model not solved to optimality.")
        println("  Termination status: ", termination_status(model))
        println("  Primal status:      ", primal_status(model))
    end
end

main()
