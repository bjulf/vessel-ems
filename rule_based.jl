using Dates, Printf, TOML

include("run_common.jl")

const BATTERY_ONLY = :battery_only
const CHARGE_ONE = :charge_one_gen
const CHARGE_TWO = :charge_two_gen
const HIGH_LOAD = :high_load

function active_generators(state)
    state == BATTERY_ONLY && return 0
    state == CHARGE_ONE && return 1
    return 2
end

function state_generator_bounds(state, gensets, preferred_total_kw)
    state == BATTERY_ONLY && return (0.0, 0.0)
    state == CHARGE_ONE && return (gensets[1].P_min, min(gensets[1].P_max, preferred_total_kw / 2))
    if state == CHARGE_TWO
        return (
            gensets[1].P_min + gensets[2].P_min,
            min(gensets[1].P_max + gensets[2].P_max, preferred_total_kw),
        )
    end
    return (
        max(gensets[1].P_min + gensets[2].P_min, preferred_total_kw),
        gensets[1].P_max + gensets[2].P_max,
    )
end

function generator_total_target(state, load_kw, preferred_generator_kw, preferred_total_kw, total_pmax)
    state == BATTERY_ONLY && return 0.0
    state == CHARGE_ONE && return preferred_generator_kw
    state == CHARGE_TWO && return preferred_total_kw
    return min(total_pmax, max(load_kw, preferred_total_kw))
end

function feasible_generator_interval(state, load_kw, max_charge_kw, max_discharge_kw, gensets, preferred_total_kw)
    state_min, state_max = state_generator_bounds(state, gensets, preferred_total_kw)
    required_min = max(0.0, load_kw - max_discharge_kw)
    required_max = load_kw + max_charge_kw

    lower = max(state_min, required_min)
    upper = min(state_max, required_max)
    lower <= upper + 1e-9 || return nothing
    return lower, upper
end

function select_generator_total(state, load_kw, max_charge_kw, max_discharge_kw, gensets, preferred_generator_kw, preferred_total_kw)
    bounds = feasible_generator_interval(state, load_kw, max_charge_kw, max_discharge_kw, gensets, preferred_total_kw)
    bounds === nothing && return nothing

    total_pmax = sum(g.P_max for g in gensets)
    target = generator_total_target(state, load_kw, preferred_generator_kw, preferred_total_kw, total_pmax)
    return clamp(target, bounds[1], bounds[2])
end

function allocate_generation(state, total_generation_kw, gensets)
    pg = zeros(Float64, length(gensets))
    n_active = active_generators(state)
    n_active == 0 && return pg

    per_generator_kw = total_generation_kw / n_active
    for g in 1:n_active
        pg[g] = per_generator_kw
    end

    return pg
end

function candidate_state_order(load_kw, previous_state, charge_latched, two_generator_latched, preferred_generator_kw, preferred_total_kw)
    states = Symbol[]

    if charge_latched
        if load_kw > preferred_total_kw + 1e-9
            append!(states, [HIGH_LOAD, CHARGE_TWO])
        elseif two_generator_latched || previous_state in (CHARGE_TWO, HIGH_LOAD)
            append!(states, [CHARGE_TWO, HIGH_LOAD])
        elseif load_kw > preferred_generator_kw + 1e-9
            append!(states, [CHARGE_TWO, HIGH_LOAD, CHARGE_ONE])
        else
            append!(states, [CHARGE_ONE, CHARGE_TWO, HIGH_LOAD])
        end
    else
        push!(states, BATTERY_ONLY)
    end

    return unique(states)
end

function battery_power_limits(battery, energy_kwh, next_energy_floor_kwh)
    energy_ceiling_kwh = battery.E_max
    max_charge_kw = min(
        battery.P_ch_max,
        max(0.0, (energy_ceiling_kwh - energy_kwh) / (battery.dt * battery.eta_ch)),
    )
    max_discharge_kw = min(
        battery.P_dis_max,
        max(0.0, (energy_kwh - next_energy_floor_kwh) * battery.eta_dis / battery.dt),
    )
    return max_charge_kw, max_discharge_kw
end

function choose_dispatch_state(
    load_kw,
    energy_kwh,
    previous_state,
    charge_latched,
    two_generator_latched,
    battery,
    gensets,
    preferred_generator_kw,
    preferred_total_kw,
    next_energy_floor_kwh,
    soc_start,
    soc_stop,
)
    soc = energy_kwh / battery.E_max
    max_charge_kw, max_discharge_kw = battery_power_limits(battery, energy_kwh, next_energy_floor_kwh)

    if charge_latched && soc >= soc_stop - 1e-9
        charge_latched = false
        two_generator_latched = false
        previous_state = BATTERY_ONLY
    elseif soc <= soc_start + 1e-9
        charge_latched = true
    end

    candidate_states = candidate_state_order(
        load_kw,
        previous_state,
        charge_latched,
        two_generator_latched,
        preferred_generator_kw,
        preferred_total_kw,
    )

    for state in candidate_states
        total_generation_kw = select_generator_total(
            state,
            load_kw,
            max_charge_kw,
            max_discharge_kw,
            gensets,
            preferred_generator_kw,
            preferred_total_kw,
        )
        total_generation_kw === nothing && continue

        if charge_latched && state in (CHARGE_TWO, HIGH_LOAD)
            two_generator_latched = true
        end

        return state, total_generation_kw, charge_latched, two_generator_latched, max_charge_kw, max_discharge_kw
    end

    error(
        "Rule-based controller could not find a feasible state for load $(load_kw) kW at energy $(round(energy_kwh; digits=2)) kWh."
    )
end

function simulate_rule_based(load, gensets, battery, initial_commitment)
    T = length(load)
    G = length(gensets)
    max_breakpoints = maximum(length(g.SFOC) for g in gensets)

    preferred_generator_kw = preferred_generator_power(gensets[1])
    preferred_total_kw = preferred_generator_kw * min(G, 2)

    u = zeros(Float64, G, T)
    y = zeros(Float64, G, T)
    Pg = zeros(Float64, G, T)
    SFOC = zeros(Float64, G, T)
    mdot = zeros(Float64, G, T)
    lambda = zeros(Float64, G, T, max_breakpoints)
    P_ch = zeros(Float64, T)
    P_dis = zeros(Float64, T)
    E = zeros(Float64, T + 1)
    E[1] = battery.E_init

    previous_state = sum(initial_commitment) == 0 ? BATTERY_ONLY : (sum(initial_commitment) == 1 ? CHARGE_ONE : CHARGE_TWO)
    previous_commitment = Float64.(initial_commitment)
    charge_latched = battery.E_init / battery.E_max <= battery.SOC_min + 1e-9
    two_generator_latched = sum(initial_commitment) >= 2

    for t in 1:T
        next_energy_floor_kwh = 0.0

        state, total_generation_kw, charge_latched, two_generator_latched, max_charge_kw, max_discharge_kw = choose_dispatch_state(
            load[t],
            E[t],
            previous_state,
            charge_latched,
            two_generator_latched,
            battery,
            gensets,
            preferred_generator_kw,
            preferred_total_kw,
            next_energy_floor_kwh,
            battery.SOC_min,
            battery.SOC_max,
        )

        pg_t = allocate_generation(state, total_generation_kw, gensets)
        net_battery_kw = load[t] - sum(pg_t)

        if net_battery_kw >= 0.0
            P_dis[t] = min(net_battery_kw, max_discharge_kw)
            P_ch[t] = 0.0
        else
            P_ch[t] = min(-net_battery_kw, max_charge_kw)
            P_dis[t] = 0.0
        end

        residual_kw = sum(pg_t) + P_dis[t] - P_ch[t] - load[t]
        abs(residual_kw) <= 1e-6 || error("Rule-based dispatch lost power balance by $(residual_kw) kW at timestep $(t).")

        E[t + 1] = E[t] + battery.dt * (battery.eta_ch * P_ch[t] - (1.0 / battery.eta_dis) * P_dis[t])

        for g in 1:G
            Pg[g, t] = pg_t[g]
            u[g, t] = pg_t[g] > 1e-9 ? 1.0 : 0.0
            y[g, t] = max(0.0, u[g, t] - previous_commitment[g])

            sfoc_g, mdot_g, lambda_g = generator_operating_point(gensets[g], Pg[g, t])
            SFOC[g, t] = sfoc_g
            mdot[g, t] = mdot_g
            lambda[g, t, 1:length(lambda_g)] = lambda_g
        end

        previous_commitment .= view(u, :, t)
        previous_state = state

        if !charge_latched
            two_generator_latched = false
        end
    end

    return (
        u = u,
        y = y,
        Pg = Pg,
        SFOC = SFOC,
        mdot = mdot,
        lambda = lambda,
        P_ch = P_ch,
        P_dis = P_dis,
        E = E,
        metadata = Dict(
            "name" => "rule_based_supervisory",
            "mode" => "rule_based",
            "soc_charge_start_pct" => battery.SOC_min * 100.0,
            "soc_charge_stop_pct" => battery.SOC_max * 100.0,
            "battery_soc_thresholds_are_soft" => true,
            "battery_energy_floor_kwh" => 0.0,
            "battery_energy_ceiling_kwh" => battery.E_max,
            "battery_charge_limit_kw" => battery.P_ch_max,
            "battery_discharge_limit_kw" => battery.P_dis_max,
            "battery_only_load_override_removed" => true,
            "preferred_generator_kw" => preferred_generator_kw,
            "preferred_two_generator_kw" => preferred_total_kw,
            "two_generator_charge_latch" => true,
            "terminal_reserve_enforced" => false,
        ),
    )
end

function equivalent_objective(results, gensets, battery)
    total_fuel_g = battery.dt * sum(results.mdot)
    startup_penalty_g = sum(gensets[g].startup_cost * results.y[g, t] for g in eachindex(gensets), t in axes(results.y, 2))
    return total_fuel_g, startup_penalty_g, total_fuel_g + startup_penalty_g
end

function main()
    started_ns = time_ns()

    config_arg = isempty(ARGS) ? joinpath("config", "baseline_model.toml") : ARGS[1]
    config_path = resolve_repo_path(config_arg)
    cfg = load_model_config(config_path)

    run_label = isempty(cfg.run_label) ? "rule_based" : "$(cfg.run_label)_rule_based"
    run_desc = isempty(cfg.run_desc) ? "Rule-based supervisory controller run" : "$(cfg.run_desc) [rule-based supervisory controller]"
    git_hash = strip(read(`git rev-parse HEAD`, String))
    git_dirty = !success(`git diff --quiet HEAD`)

    load_profile_path = cfg.load_profile_path
    isfile(load_profile_path) || error(
        "Missing $(load_profile_path) referenced by $(config_path)."
    )
    load, datetimes = read_load_profile(load_profile_path)

    results = simulate_rule_based(load, cfg.gensets, cfg.battery, cfg.initial_commitment)
    total_fuel_g, startup_penalty_g, equivalent_cost_g = equivalent_objective(results, cfg.gensets, cfg.battery)
    elapsed_s = (time_ns() - started_ns) / 1e9

    validation = validation_metadata(
        load,
        datetimes,
        cfg.battery,
        results.Pg,
        results.P_ch,
        results.P_dis,
        results.E;
        primal_tolerance=1e-6,
        mip_tolerance=0.0,
        energy_tolerance=1e-6,
    )

    timestamp = Dates.format(now(), "yyyy-mm-dd_HHMMSS")
    run_dir = joinpath(@__DIR__, "runs", "$(timestamp)_$(run_label)")
    mkpath(run_dir)

    params_dict = Dict(
        "run" => Dict(
            "date" => Dates.format(now(), "yyyy-mm-dd"),
            "label" => run_label,
            "description" => run_desc,
            "git_hash" => git_hash,
            "git_dirty" => git_dirty,
            "config_file" => config_path,
            "method" => "rule_based",
        ),
        "solver" => Dict(
            "status" => "SIMULATED",
            "equivalent_cost_g" => equivalent_cost_g,
            "solve_time_s" => elapsed_s,
        ),
        "controller" => merge(
            copy(results.metadata),
            Dict(
                "fuel_g" => total_fuel_g,
                "startup_penalty_g" => startup_penalty_g,
                "equivalent_cost_g" => equivalent_cost_g,
            ),
        ),
        "validation" => validation,
        "battery" => battery_energy_metadata(cfg.battery),
        "initial_conditions" => Dict(
            "generator_commitment" => collect(cfg.initial_commitment),
            "battery_energy_kwh" => cfg.battery.E_init,
        ),
        "terminal_conditions" => Dict(
            "battery_energy_min_kwh" => cfg.battery.E_terminal_min,
        ),
        "load_profile" => Dict(
            "source_file" => load_profile_path,
            "timesteps" => length(load),
            "start_datetime" => datetimes[1],
            "end_datetime" => datetimes[end],
            "dt_minutes" => cfg.dt_minutes,
        ),
        "generators" => [
            Dict(
                "P_max" => g.P_max,
                "P_min" => g.P_min,
                "P" => collect(Float64, g.P),
                "SFOC" => collect(Float64, g.SFOC),
                "startup_cost" => g.startup_cost,
            )
            for g in cfg.gensets
        ],
    )
    open(joinpath(run_dir, "params.toml"), "w") do io
        TOML.print(io, params_dict)
    end

    csv_path = joinpath(run_dir, "dispatch_results.csv")
    write_results_csv(csv_path, load, datetimes, cfg.gensets, cfg.battery, results)

    open(joinpath(@__DIR__, ".current_run"), "w") do io
        write(io, run_dir)
    end

    println("Equivalent cost = ", @sprintf("%.2f", equivalent_cost_g), " g")
    println("Fuel used       = ", @sprintf("%.2f", total_fuel_g), " g")
    println("Starts penalty  = ", @sprintf("%.2f", startup_penalty_g), " g")
    println("Run saved to    -> ", run_dir)
end

main()
