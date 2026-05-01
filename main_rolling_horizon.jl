using JuMP, HiGHS, Printf, Dates, TOML, Statistics

include("model.jl")
include("run_common.jl")

const MOI = JuMP.MOI

solver_option(model, name) = Float64(MOI.get(backend(model), MOI.RawOptimizerAttribute(name)))

function extract_results(load, gensets, u, y, Pg, mdot, lambda, P_ch, P_dis, E)
    G = 1:length(gensets)
    T = 1:length(load)
    max_breakpoints = maximum(length(g.SFOC) for g in gensets)

    return (
        u = [value(u[g, t]) for g in G, t in T],
        y = [value(y[g, t]) for g in G, t in T],
        Pg = [value(Pg[g, t]) for g in G, t in T],
        mdot = [value(mdot[g, t]) for g in G, t in T],
        lambda = [
            i <= length(gensets[g].SFOC) ? value(lambda[g, t, i]) : 0.0
            for g in G, t in T, i in 1:max_breakpoints
        ],
        P_ch = [value(P_ch[t]) for t in T],
        P_dis = [value(P_dis[t]) for t in T],
        E = [value(E[t]) for t in 1:(length(load) + 1)],
    )
end

function load_rolling_settings(config_path)
    raw = TOML.parsefile(config_path)
    rolling_cfg = get(raw, "rolling_horizon", Dict{String, Any}())
    solver_cfg = get(raw, "solver", Dict{String, Any}())
    soc_strategy = String(get(rolling_cfg, "soc_strategy", haskey(raw, "soft_soc") ? "soft_band" : "terminal_reserve"))
    soc_strategy in ("soft_band", "terminal_reserve") || error(
        "Unsupported rolling_horizon.soc_strategy=$(soc_strategy). Supported values are: soft_band, terminal_reserve."
    )
    forecast_settings = forecast_settings_from_config(rolling_cfg)

    soft_soc_cfg = soc_strategy == "soft_band" ? required_key(raw, "soft_soc", config_path) : Dict{String, Any}()

    return (
        horizon_steps = Int(get(rolling_cfg, "horizon_steps", 24)),
        soc_strategy = soc_strategy,
        min_up_time_steps = Int(get(rolling_cfg, "min_up_time_steps", 1)),
        soft_band_terminal_reserve_enabled = Bool(get(rolling_cfg, "soft_band_terminal_reserve_enabled", false)),
        terminal_soc_target = Float64(get(rolling_cfg, "terminal_soc_target", 0.50)),
        terminal_slack_penalty_g_per_kwh = Float64(
            get(rolling_cfg, "terminal_slack_penalty_g_per_kwh", 10000.0)
        ),
        forecast_method = forecast_settings.forecast_method,
        moving_average_window_steps = forecast_settings.moving_average_window_steps,
        tail_forecast_policy = forecast_settings.tail_forecast_policy,
        local_solve_time_limit_sec = Float64(
            get(solver_cfg, "rolling_local_time_limit_sec", get(rolling_cfg, "local_solve_time_limit_sec", 0.0))
        ),
        progress_log_enabled = Bool(
            get(solver_cfg, "progress_log_enabled", get(rolling_cfg, "progress_log_enabled", true))
        ),
        progress_log_every_steps = Int(
            get(solver_cfg, "progress_log_every_steps", get(rolling_cfg, "progress_log_every_steps", 10))
        ),
        slow_solve_log_threshold_sec = Float64(
            get(solver_cfg, "slow_solve_log_threshold_sec", get(rolling_cfg, "slow_solve_log_threshold_sec", 5.0))
        ),
        preferred_soc_min = soc_strategy == "soft_band" ? Float64(required_key(soft_soc_cfg, "preferred_soc_min", "[soft_soc]")) : NaN,
        preferred_soc_max = soc_strategy == "soft_band" ? Float64(required_key(soft_soc_cfg, "preferred_soc_max", "[soft_soc]")) : NaN,
        soc_min_penalty_g_per_kwh = soc_strategy == "soft_band" ? Float64(required_key(soft_soc_cfg, "soc_min_penalty_g_per_kwh", "[soft_soc]")) : NaN,
        soc_max_penalty_g_per_kwh = soc_strategy == "soft_band" ? Float64(required_key(soft_soc_cfg, "soc_max_penalty_g_per_kwh", "[soft_soc]")) : NaN,
        soft_soc_penalty_scaling = soc_strategy == "soft_band" ? String(get(soft_soc_cfg, "soft_soc_penalty_scaling", "sum")) : "",
    )
end

function validate_rolling_solver_settings(settings)
    settings.local_solve_time_limit_sec >= 0.0 || error(
        "rolling_local_time_limit_sec must be >= 0. Use 0 to disable the local time limit."
    )
    settings.progress_log_every_steps >= 1 || error(
        "progress_log_every_steps must be >= 1."
    )
    settings.slow_solve_log_threshold_sec >= 0.0 || error(
        "slow_solve_log_threshold_sec must be >= 0."
    )
    settings.min_up_time_steps >= 1 || error(
        "rolling_horizon.min_up_time_steps must be >= 1; got $(settings.min_up_time_steps)."
    )
    0.0 <= settings.terminal_soc_target <= 1.0 || error(
        "rolling_horizon.terminal_soc_target must be in [0, 1]; got $(settings.terminal_soc_target)."
    )
    settings.terminal_slack_penalty_g_per_kwh >= 0.0 || error(
        "rolling_horizon.terminal_slack_penalty_g_per_kwh must be >= 0."
    )
    if settings.soft_band_terminal_reserve_enabled && settings.soc_strategy != "soft_band"
        error("rolling_horizon.soft_band_terminal_reserve_enabled only applies when soc_strategy=\"soft_band\".")
    end
    if settings.soc_strategy == "soft_band"
        settings.soft_soc_penalty_scaling in ("sum", "mean") || error(
            "Unsupported soft_soc.soft_soc_penalty_scaling=$(settings.soft_soc_penalty_scaling). Supported values are: sum, mean."
        )
    end
end

function progress_step_due(r, n_steps, settings)
    return settings.progress_log_enabled && (
        r == 1 ||
        r == n_steps ||
        r % settings.progress_log_every_steps == 0
    )
end

function percentile(sorted_values, p)
    isempty(sorted_values) && return NaN
    length(sorted_values) == 1 && return sorted_values[1]

    pos = 1.0 + (length(sorted_values) - 1) * p
    lo = floor(Int, pos)
    hi = ceil(Int, pos)
    lo == hi && return sorted_values[lo]

    weight = pos - lo
    return (1.0 - weight) * sorted_values[lo] + weight * sorted_values[hi]
end

function preferred_soc_slacks(E, battery, settings)
    e_min = settings.preferred_soc_min * battery.E_max
    e_max = settings.preferred_soc_max * battery.E_max
    lower = [max(0.0, e_min - e) for e in E]
    upper = [max(0.0, e - e_max) for e in E]
    return lower, upper
end

function dispatch_kpis(
    results,
    gensets,
    battery,
    settings;
    solve_times=Float64[],
    terminal_slacks=Float64[],
    local_soc_min_slacks=Float64[],
    local_soc_max_slacks=Float64[],
    nonoptimal_count=0,
)
    total_fuel_g = battery.dt * sum(results.mdot)
    startup_count = sum(results.y .> 0.5)
    min_soc_pct = minimum(results.E) / battery.E_max * 100.0
    max_soc_pct = maximum(results.E) / battery.E_max * 100.0
    final_soc_pct = results.E[end] / battery.E_max * 100.0
    sorted_times = sort(collect(solve_times))

    kpis = Dict(
        "total_fuel_g" => total_fuel_g,
        "total_fuel_kg" => total_fuel_g / 1000.0,
        "generator_starts" => startup_count,
        "minimum_soc_pct" => min_soc_pct,
        "maximum_soc_pct" => max_soc_pct,
        "final_soc_pct" => final_soc_pct,
        "median_solve_time_s" => isempty(sorted_times) ? NaN : median(sorted_times),
        "p95_solve_time_s" => isempty(sorted_times) ? NaN : percentile(sorted_times, 0.95),
        "maximum_solve_time_s" => isempty(sorted_times) ? NaN : maximum(sorted_times),
        "nonoptimal_timeout_or_infeasible_solves" => nonoptimal_count,
    )

    if settings.soc_strategy == "soft_band"
        realized_min_slack, realized_max_slack = preferred_soc_slacks(results.E, battery, settings)
        merge!(
            kpis,
            Dict(
                "realized_total_soc_min_slack_kwh" => sum(realized_min_slack),
                "realized_maximum_soc_min_slack_kwh" => maximum(realized_min_slack),
                "realized_soc_min_violation_states" => count(>(1e-9), realized_min_slack),
                "realized_total_soc_max_slack_kwh" => sum(realized_max_slack),
                "realized_maximum_soc_max_slack_kwh" => maximum(realized_max_slack),
                "realized_soc_max_violation_states" => count(>(1e-9), realized_max_slack),
                "local_total_soc_min_slack_kwh" => isempty(local_soc_min_slacks) ? 0.0 : sum(local_soc_min_slacks),
                "local_maximum_soc_min_slack_kwh" => isempty(local_soc_min_slacks) ? 0.0 : maximum(local_soc_min_slacks),
                "local_total_soc_max_slack_kwh" => isempty(local_soc_max_slacks) ? 0.0 : sum(local_soc_max_slacks),
                "local_maximum_soc_max_slack_kwh" => isempty(local_soc_max_slacks) ? 0.0 : maximum(local_soc_max_slacks),
            )
        )
        if settings.soft_band_terminal_reserve_enabled
            valid_terminal_slacks = filter(x -> !isnan(x), terminal_slacks)
            merge!(
                kpis,
                Dict(
                    "total_terminal_slack_kwh" => isempty(valid_terminal_slacks) ? 0.0 : sum(valid_terminal_slacks),
                    "maximum_terminal_slack_kwh" => isempty(valid_terminal_slacks) ? 0.0 : maximum(valid_terminal_slacks),
                )
            )
        end
    else
        merge!(
            kpis,
            Dict(
                "total_terminal_slack_kwh" => isempty(terminal_slacks) ? 0.0 : sum(terminal_slacks),
                "maximum_terminal_slack_kwh" => isempty(terminal_slacks) ? 0.0 : maximum(terminal_slacks),
            )
        )
    end

    return kpis
end

function solve_full_horizon_benchmark(cfg, load, show_solver_log)
    model, u, y, Pg, mdot, lambda, P_ch, P_dis, E = build_model_baseline(
        cfg.gensets,
        load,
        cfg.battery,
        cfg.initial_commitment,
    )

    if !show_solver_log
        set_silent(model)
    end

    optimize!(model)
    termination_status(model) == OPTIMAL || error(
        "Full-horizon benchmark did not solve to optimality. Status: $(termination_status(model)); primal status: $(primal_status(model))."
    )

    return (
        model = model,
        results = extract_results(load, cfg.gensets, u, y, Pg, mdot, lambda, P_ch, P_dis, E),
    )
end

function solve_rolling_horizon(cfg, load, datetimes, rolling_settings, show_solver_log)
    gensets = cfg.gensets
    battery = cfg.battery
    G = 1:length(gensets)
    T = 1:length(load)
    H = rolling_settings.horizon_steps
    max_breakpoints = maximum(length(g.SFOC) for g in gensets)
    terminal_target_kwh = rolling_settings.terminal_soc_target * battery.E_max

    u_real = zeros(Float64, length(G), length(T))
    y_real = zeros(Float64, length(G), length(T))
    Pg_real = zeros(Float64, length(G), length(T))
    mdot_real = zeros(Float64, length(G), length(T))
    lambda_real = zeros(Float64, length(G), length(T), max_breakpoints)
    P_ch_real = zeros(Float64, length(T))
    P_dis_real = zeros(Float64, length(T))
    E_real = zeros(Float64, length(T) + 1)
    E_real[1] = battery.E_init

    previous_commitment = collect(cfg.initial_commitment)
    prior_on_duration_steps = [
        previous_commitment[g] > 0.5 ? rolling_settings.min_up_time_steps : 0
        for g in G
    ]
    solve_times = Float64[]
    terminal_slacks = Float64[]
    local_terminal_energy = Float64[]
    local_soc_min_slacks = Float64[]
    local_soc_max_slacks = Float64[]
    local_soc_min_slack_max = Float64[]
    local_soc_max_slack_max = Float64[]
    statuses = String[]
    primal_statuses = String[]
    padded_steps = Int[]
    forecast_first_load = Float64[]
    forecast_mean_load = Float64[]
    nonoptimal_count = 0
    n_steps = length(load)

    for r in T
        forecast = rolling_load_forecast(load, r, H, rolling_settings)
        push!(padded_steps, rolling_forecast_tail_padded_steps(load, r, H, rolling_settings))
        push!(forecast_first_load, forecast[1])
        push!(forecast_mean_load, sum(forecast) / length(forecast))
        local_battery = merge(battery, (E_init = E_real[r],))

        components = if rolling_settings.soc_strategy == "soft_band"
            build_rolling_horizon_soft_soc_milp(
                gensets,
                forecast,
                local_battery,
                previous_commitment,
                rolling_settings.preferred_soc_min,
                rolling_settings.preferred_soc_max,
                rolling_settings.soc_min_penalty_g_per_kwh,
                rolling_settings.soc_max_penalty_g_per_kwh;
                soft_soc_penalty_scaling=rolling_settings.soft_soc_penalty_scaling,
                min_up_time_steps=rolling_settings.min_up_time_steps,
                prior_on_duration_steps=prior_on_duration_steps,
                terminal_soft_target_kwh=rolling_settings.soft_band_terminal_reserve_enabled ? terminal_target_kwh : nothing,
                terminal_slack_penalty=rolling_settings.terminal_slack_penalty_g_per_kwh,
            )
        else
            build_rolling_horizon_milp(
                gensets,
                forecast,
                local_battery,
                previous_commitment,
                terminal_target_kwh,
                rolling_settings.terminal_slack_penalty_g_per_kwh,
            )
        end

        if rolling_settings.local_solve_time_limit_sec > 0.0
            set_time_limit_sec(components.model, rolling_settings.local_solve_time_limit_sec)
        end
        if !show_solver_log
            set_silent(components.model)
        end

        if progress_step_due(r, n_steps, rolling_settings)
            @printf(
                "Rolling solve %d/%d starting: load=%.3f kW, E_init=%.3f kWh, forecast_mean=%.3f kW\n",
                r,
                n_steps,
                load[r],
                E_real[r],
                forecast_mean_load[end],
            )
            flush(stdout)
        end

        optimize!(components.model)
        status = termination_status(components.model)
        pstatus = primal_status(components.model)
        local_solve_time = solve_time(components.model)
        push!(statuses, string(status))
        push!(primal_statuses, string(pstatus))
        push!(solve_times, local_solve_time)

        if status != OPTIMAL
            nonoptimal_count += 1
            has_values(components.model) || error(
                "Rolling $(rolling_settings.soc_strategy) update $(r) has no implementable incumbent. Status: $(status); primal status: $(pstatus)."
            )
        end

        for g in G
            u_real[g, r] = value(components.u[g, 1])
            y_real[g, r] = value(components.y[g, 1])
            Pg_real[g, r] = value(components.Pg[g, 1])
            mdot_real[g, r] = value(components.mdot[g, 1])
            for i in 1:length(gensets[g].SFOC)
                lambda_real[g, r, i] = value(components.lambda[g, 1, i])
            end
        end

        P_ch_real[r] = value(components.P_ch[1])
        P_dis_real[r] = value(components.P_dis[1])
        E_real[r + 1] = E_real[r] + battery.dt * (
            battery.eta_ch * P_ch_real[r] -
            (1.0 / battery.eta_dis) * P_dis_real[r]
        )

        if (
            progress_step_due(r, n_steps, rolling_settings) ||
            status != OPTIMAL ||
            local_solve_time >= rolling_settings.slow_solve_log_threshold_sec
        )
            @printf(
                "Rolling solve %d/%d done: status=%s, primal=%s, solve=%.3f s, E_next=%.3f kWh, commitment=%s\n",
                r,
                n_steps,
                string(status),
                string(pstatus),
                local_solve_time,
                E_real[r + 1],
                string([u_real[g, r] > 0.5 ? 1 : 0 for g in G]),
            )
            flush(stdout)
        end

        if rolling_settings.soc_strategy == "soft_band"
            local_min_slacks = [value(components.soc_min_slack[e]) for e in 1:(H + 1)]
            local_max_slacks = [value(components.soc_max_slack[e]) for e in 1:(H + 1)]
            push!(local_soc_min_slacks, sum(local_min_slacks))
            push!(local_soc_max_slacks, sum(local_max_slacks))
            push!(local_soc_min_slack_max, maximum(local_min_slacks))
            push!(local_soc_max_slack_max, maximum(local_max_slacks))
            if rolling_settings.soft_band_terminal_reserve_enabled
                push!(terminal_slacks, value(components.terminal_slack))
                push!(local_terminal_energy, value(components.E[H + 1]))
            else
                push!(terminal_slacks, NaN)
                push!(local_terminal_energy, NaN)
            end
        else
            push!(terminal_slacks, value(components.terminal_slack))
            push!(local_terminal_energy, value(components.E[H + 1]))
        end
        previous_commitment = [u_real[g, r] > 0.5 ? 1 : 0 for g in G]
        prior_on_duration_steps = [
            previous_commitment[g] == 1 ? prior_on_duration_steps[g] + 1 : 0
            for g in G
        ]
    end

    results = (
        u = u_real,
        y = y_real,
        Pg = Pg_real,
        mdot = mdot_real,
        lambda = lambda_real,
        P_ch = P_ch_real,
        P_dis = P_dis_real,
        E = E_real,
    )

    return (
        results = results,
        solve_times = solve_times,
        terminal_slacks = terminal_slacks,
        local_terminal_energy = local_terminal_energy,
        local_soc_min_slacks = local_soc_min_slacks,
        local_soc_max_slacks = local_soc_max_slacks,
        local_soc_min_slack_max = local_soc_min_slack_max,
        local_soc_max_slack_max = local_soc_max_slack_max,
        statuses = statuses,
        primal_statuses = primal_statuses,
        padded_steps = padded_steps,
        forecast_first_load = forecast_first_load,
        forecast_mean_load = forecast_mean_load,
        nonoptimal_count = nonoptimal_count,
        forecast_method = rolling_settings.forecast_method,
        moving_average_window_steps = rolling_settings.moving_average_window_steps,
        soc_strategy = rolling_settings.soc_strategy,
        min_up_time_steps = rolling_settings.min_up_time_steps,
        soft_band_terminal_reserve_enabled = rolling_settings.soft_band_terminal_reserve_enabled,
    )
end

function write_local_solve_csv(path, datetimes, load, rolling)
    open(path, "w") do io
        if rolling.soc_strategy == "soft_band"
            header = [
                "update",
                "datetime",
                "termination_status",
                "primal_status",
                "solve_time_s",
                "local_soc_min_slack_sum_kwh",
                "local_soc_min_slack_max_kwh",
                "local_soc_max_slack_sum_kwh",
                "local_soc_max_slack_max_kwh",
            ]
            if rolling.soft_band_terminal_reserve_enabled
                append!(header, [
                    "soft_band_terminal_reserve_enabled",
                    "terminal_slack_kwh",
                    "local_terminal_energy_kwh",
                ])
            end
            append!(header, [
                "forecast_method",
                "moving_average_window_steps",
                "realized_load_kw",
                "forecast_first_load_kw",
                "forecast_mean_load_kw",
                "tail_padded_steps",
            ])
            println(io, join(header, ","))
        else
            println(io, join([
                "update",
                "datetime",
                "termination_status",
                "primal_status",
                "solve_time_s",
                "terminal_slack_kwh",
                "local_terminal_energy_kwh",
                "forecast_method",
                "moving_average_window_steps",
                "realized_load_kw",
                "forecast_first_load_kw",
                "forecast_mean_load_kw",
                "tail_padded_steps",
            ], ","))
        end

        for r in eachindex(datetimes)
            row = if rolling.soc_strategy == "soft_band"
                soft_row = [
                    string(r),
                    datetimes[r],
                    rolling.statuses[r],
                    rolling.primal_statuses[r],
                    format_num(rolling.solve_times[r]),
                    format_num(rolling.local_soc_min_slacks[r]),
                    format_num(rolling.local_soc_min_slack_max[r]),
                    format_num(rolling.local_soc_max_slacks[r]),
                    format_num(rolling.local_soc_max_slack_max[r]),
                ]
                if rolling.soft_band_terminal_reserve_enabled
                    append!(soft_row, [
                        string(rolling.soft_band_terminal_reserve_enabled),
                        format_num(rolling.terminal_slacks[r]),
                        format_num(rolling.local_terminal_energy[r]),
                    ])
                end
                append!(soft_row, [
                    rolling.forecast_method,
                    string(rolling.moving_average_window_steps),
                    format_num(load[r]),
                    format_num(rolling.forecast_first_load[r]),
                    format_num(rolling.forecast_mean_load[r]),
                    string(rolling.padded_steps[r]),
                ])
                soft_row
            else
                [
                    string(r),
                    datetimes[r],
                    rolling.statuses[r],
                    rolling.primal_statuses[r],
                    format_num(rolling.solve_times[r]),
                    format_num(rolling.terminal_slacks[r]),
                    format_num(rolling.local_terminal_energy[r]),
                    rolling.forecast_method,
                    string(rolling.moving_average_window_steps),
                    format_num(load[r]),
                    format_num(rolling.forecast_first_load[r]),
                    format_num(rolling.forecast_mean_load[r]),
                    string(rolling.padded_steps[r]),
                ]
            end
            println(io, join(row, ","))
        end
    end
end

function comparison_metadata(rolling_kpis, benchmark_kpis)
    return Dict(
        "fuel_delta_g" => rolling_kpis["total_fuel_g"] - benchmark_kpis["total_fuel_g"],
        "fuel_delta_pct" => (
            (rolling_kpis["total_fuel_g"] - benchmark_kpis["total_fuel_g"]) /
            benchmark_kpis["total_fuel_g"] * 100.0
        ),
        "generator_starts_delta" => rolling_kpis["generator_starts"] - benchmark_kpis["generator_starts"],
        "minimum_soc_delta_pct_points" => rolling_kpis["minimum_soc_pct"] - benchmark_kpis["minimum_soc_pct"],
        "final_soc_delta_pct_points" => rolling_kpis["final_soc_pct"] - benchmark_kpis["final_soc_pct"],
    )
end

function main()
    config_arg = isempty(ARGS) ? joinpath("config", "rolling_horizon_operational.toml") : ARGS[1]
    config_path = resolve_repo_path(config_arg)
    cfg = load_model_config(config_path)
    rolling_settings = load_rolling_settings(config_path)
    validate_rolling_solver_settings(rolling_settings)

    cfg.dt_minutes == 15 || error(
        "MVP rolling-horizon controller expects dt_minutes=15 (Delta t = 0.25 h); got $(cfg.dt_minutes)."
    )
    rolling_settings.horizon_steps >= 1 || error(
        "rolling_horizon.horizon_steps must be >= 1; got $(rolling_settings.horizon_steps)."
    )
    if rolling_settings.soc_strategy == "soft_band"
        0.0 <= rolling_settings.preferred_soc_min <= rolling_settings.preferred_soc_max <= 1.0 || error(
            "Expected 0 <= preferred_soc_min <= preferred_soc_max <= 1."
        )
    end

    isfile(cfg.load_profile_path) || error(
        "Missing $(cfg.load_profile_path) referenced by $(config_path)."
    )
    load, datetimes = read_load_profile(cfg.load_profile_path)

    show_solver_log = cfg.show_solver_log
    git_hash = strip(read(`git rev-parse HEAD`, String))
    git_dirty = !success(`git diff --quiet HEAD`)

    println("Solving full-horizon benchmark for ", length(load), " timesteps...")
    flush(stdout)
    benchmark = solve_full_horizon_benchmark(cfg, load, show_solver_log)
    println("Full-horizon benchmark status = ", termination_status(benchmark.model), ", solve time = ", @sprintf("%.3f", solve_time(benchmark.model)), " s")
    println(
        "Solving rolling horizon: strategy=", rolling_settings.soc_strategy,
        ", forecast=", rolling_settings.forecast_method,
        ", local time limit=",
        rolling_settings.local_solve_time_limit_sec > 0.0 ? @sprintf("%.1f s", rolling_settings.local_solve_time_limit_sec) : "disabled",
        ", progress every ", rolling_settings.progress_log_every_steps, " steps",
    )
    flush(stdout)
    rolling = solve_rolling_horizon(cfg, load, datetimes, rolling_settings, show_solver_log)

    primal_tol = solver_option(benchmark.model, "primal_feasibility_tolerance")
    mip_tol = solver_option(benchmark.model, "mip_feasibility_tolerance")

    rolling_kpis = dispatch_kpis(
        rolling.results,
        cfg.gensets,
        cfg.battery,
        rolling_settings;
        solve_times=rolling.solve_times,
        terminal_slacks=rolling.terminal_slacks,
        local_soc_min_slacks=rolling.local_soc_min_slacks,
        local_soc_max_slacks=rolling.local_soc_max_slacks,
        nonoptimal_count=rolling.nonoptimal_count,
    )
    benchmark_kpis = dispatch_kpis(
        benchmark.results,
        cfg.gensets,
        cfg.battery,
        rolling_settings;
        solve_times=[solve_time(benchmark.model)],
    )

    timestamp = Dates.format(now(), "yyyy-mm-dd_HHMMSS")
    run_dir = joinpath(@__DIR__, "runs", "$(timestamp)_$(cfg.run_label)")
    mkpath(run_dir)

    rolling_validation = validation_metadata(
        load,
        datetimes,
        cfg.battery,
        rolling.results.Pg,
        rolling.results.P_ch,
        rolling.results.P_dis,
        rolling.results.E;
        primal_tolerance=primal_tol,
        mip_tolerance=mip_tol,
        energy_tolerance=primal_tol,
    )
    benchmark_validation = validation_metadata(
        load,
        datetimes,
        cfg.battery,
        benchmark.results.Pg,
        benchmark.results.P_ch,
        benchmark.results.P_dis,
        benchmark.results.E;
        primal_tolerance=primal_tol,
        mip_tolerance=mip_tol,
        energy_tolerance=primal_tol,
    )

    params_dict = Dict(
        "run" => Dict(
            "date"        => Dates.format(now(), "yyyy-mm-dd"),
            "label"       => cfg.run_label,
            "description" => cfg.run_desc,
            "git_hash"    => git_hash,
            "git_dirty"   => git_dirty,
            "config_file" => config_path,
            "entry_point" => "main_rolling_horizon.jl",
            "model_file"  => "model.jl",
            "controller"  => "rolling_horizon",
        ),
        "rolling_horizon" => merge(
            Dict(
                "update_index" => "r",
                "horizon_steps" => rolling_settings.horizon_steps,
                "dt_h" => cfg.battery.dt,
                "implemented_steps_per_update" => 1,
                "soc_strategy" => rolling_settings.soc_strategy,
                "min_up_time_steps" => rolling_settings.min_up_time_steps,
                "forecast_method" => rolling_settings.forecast_method,
                "moving_average_window_steps" => rolling_settings.moving_average_window_steps,
                "local_load_definition" => rolling_forecast_definition(rolling_settings),
                "uses_realized_future_load_inside_local_horizon" => rolling_forecast_uses_realized_future_load(rolling_settings),
                "uses_full_horizon_soc_reference" => false,
                "full_horizon_soc_tracking" => "not used as a hard constraint, soft target, reference, or penalty target",
                "full_horizon_solution_role" => "offline lower-bound objective benchmark only",
                "tail_forecast_policy" => rolling_settings.tail_forecast_policy,
                "tail_forecast_padded_solves" => count(>(0), rolling.padded_steps),
                "tail_forecast_total_padded_steps" => sum(rolling.padded_steps),
                "local_solve_time_limit_sec" => rolling_settings.local_solve_time_limit_sec,
                "progress_log_enabled" => rolling_settings.progress_log_enabled,
                "progress_log_every_steps" => rolling_settings.progress_log_every_steps,
                "slow_solve_log_threshold_sec" => rolling_settings.slow_solve_log_threshold_sec,
            ),
            rolling_settings.soc_strategy == "soft_band" ? Dict(
                "terminal_reserve_constraint_enabled" => rolling_settings.soft_band_terminal_reserve_enabled,
                "local_soc_interpretation" => "preferred SOC operating band with soft violations over each local horizon",
                "soft_soc_penalty_scaling" => rolling_settings.soft_soc_penalty_scaling,
                "soft_soc_penalty_objective" => rolling_settings.soft_soc_penalty_scaling == "mean" ?
                    "c_SOC^- * (1 / (H + 1)) * sum(s_e^-) + c_SOC^+ * (1 / (H + 1)) * sum(s_e^+)" :
                    "c_SOC^- * sum(s_e^-) + c_SOC^+ * sum(s_e^+)",
                "soft_band_terminal_reserve_enabled" => rolling_settings.soft_band_terminal_reserve_enabled,
                "terminal_soc_target" => rolling_settings.soft_band_terminal_reserve_enabled ? rolling_settings.terminal_soc_target : 0.0,
                "terminal_energy_target_kwh" => rolling_settings.soft_band_terminal_reserve_enabled ? rolling_settings.terminal_soc_target * cfg.battery.E_max : 0.0,
                "terminal_slack_penalty_g_per_kwh" => rolling_settings.soft_band_terminal_reserve_enabled ? rolling_settings.terminal_slack_penalty_g_per_kwh : 0.0,
                "terminal_constraint" => rolling_settings.soft_band_terminal_reserve_enabled ? "E_local[H+1] + s_term >= E_term, s_term >= 0" : "not enabled",
            ) : Dict(
                "terminal_reserve_constraint_enabled" => true,
                "terminal_soc_target" => rolling_settings.terminal_soc_target,
                "terminal_energy_target_kwh" => rolling_settings.terminal_soc_target * cfg.battery.E_max,
                "terminal_slack_penalty_g_per_kwh" => rolling_settings.terminal_slack_penalty_g_per_kwh,
                "terminal_constraint" => "E_local[H+1] + s_term >= E_term, s_term >= 0",
                "terminal_target_interpretation" => "one-sided soft reserve target, not a physical battery limit or exact SOC tracking constraint",
            )
        ),
        "solver" => Dict(
            "rolling_local_solves" => length(load),
            "benchmark_status" => string(termination_status(benchmark.model)),
            "benchmark_objective" => objective_value(benchmark.model),
            "benchmark_solve_time_s" => solve_time(benchmark.model),
        ),
        "kpis" => Dict(
            "rolling_horizon" => rolling_kpis,
            "full_horizon_benchmark" => benchmark_kpis,
            "comparison" => comparison_metadata(rolling_kpis, benchmark_kpis),
        ),
        "validation" => Dict(
            "rolling_horizon" => rolling_validation,
            "full_horizon_benchmark" => benchmark_validation,
        ),
        "battery" => battery_energy_metadata(cfg.battery),
        "initial_conditions" => Dict(
            "generator_commitment" => collect(cfg.initial_commitment),
            "battery_energy_kwh"   => cfg.battery.E_init,
        ),
        "terminal_conditions" => Dict(
            "battery_energy_min_kwh_reference" => cfg.battery.E_terminal_min,
            "full_horizon_constraint_enforced" => false,
            "rolling_local_terminal_constraint_enforced" => (
                rolling_settings.soc_strategy == "terminal_reserve" ||
                rolling_settings.soft_band_terminal_reserve_enabled
            ),
            "rolling_local_soft_soc_band_enforced" => rolling_settings.soc_strategy == "soft_band",
        ),
        "load_profile" => Dict(
            "source_file"     => cfg.load_profile_path,
            "timesteps"       => length(load),
            "start_datetime"  => datetimes[1],
            "end_datetime"    => datetimes[end],
            "dt_minutes"      => cfg.dt_minutes,
        ),
        "generators" => [
            Dict(
                "P_max"        => g.P_max,
                "P_min"        => g.P_min,
                "P"            => collect(Float64, g.P),
                "SFOC"         => collect(Float64, g.SFOC),
                "startup_cost" => g.startup_cost,
                "shutdown_cost" => g.shutdown_cost,
            )
            for g in cfg.gensets
        ],
    )

    if rolling_settings.soc_strategy == "soft_band"
        params_dict["soft_soc"] = Dict(
            "preferred_soc_min" => rolling_settings.preferred_soc_min,
            "preferred_soc_max" => rolling_settings.preferred_soc_max,
            "preferred_energy_min_kwh" => rolling_settings.preferred_soc_min * cfg.battery.E_max,
            "preferred_energy_max_kwh" => rolling_settings.preferred_soc_max * cfg.battery.E_max,
            "soc_min_penalty_g_per_kwh" => rolling_settings.soc_min_penalty_g_per_kwh,
            "soc_max_penalty_g_per_kwh" => rolling_settings.soc_max_penalty_g_per_kwh,
            "soft_soc_penalty_scaling" => rolling_settings.soft_soc_penalty_scaling,
            "min_up_time_steps" => rolling_settings.min_up_time_steps,
            "soft_band_terminal_reserve_enabled" => rolling_settings.soft_band_terminal_reserve_enabled,
            "terminal_soc_target" => rolling_settings.soft_band_terminal_reserve_enabled ? rolling_settings.terminal_soc_target : 0.0,
            "terminal_energy_target_kwh" => rolling_settings.soft_band_terminal_reserve_enabled ? rolling_settings.terminal_soc_target * cfg.battery.E_max : 0.0,
            "terminal_slack_penalty_g_per_kwh" => rolling_settings.soft_band_terminal_reserve_enabled ? rolling_settings.terminal_slack_penalty_g_per_kwh : 0.0,
            "physical_energy_lower_kwh" => 0.0,
            "physical_energy_upper_kwh" => cfg.battery.E_max,
            "interpretation" => rolling_settings.soft_soc_penalty_scaling == "mean" ?
                "Preferred rolling-horizon operating band with average soft violations over local energy states; not a terminal reserve constraint." :
                "Preferred rolling-horizon operating band with summed soft violations over local energy states; not a terminal reserve constraint.",
        )
    end

    open(joinpath(run_dir, "params.toml"), "w") do io
        TOML.print(io, params_dict)
    end

    write_results_csv(
        joinpath(run_dir, "dispatch_results.csv"),
        load,
        datetimes,
        cfg.gensets,
        cfg.battery,
        rolling.results,
    )
    write_results_csv(
        joinpath(run_dir, "full_horizon_benchmark_dispatch_results.csv"),
        load,
        datetimes,
        cfg.gensets,
        cfg.battery,
        benchmark.results,
    )
    write_local_solve_csv(joinpath(run_dir, "rolling_local_solves.csv"), datetimes, load, rolling)

    open(joinpath(@__DIR__, ".current_run"), "w") do io
        write(io, run_dir)
    end

    comparison = comparison_metadata(rolling_kpis, benchmark_kpis)
    println("Rolling-horizon run saved to -> ", run_dir)
    println("SOC strategy       = ", rolling_settings.soc_strategy)
    println("Rolling fuel       = ", @sprintf("%.3f", rolling_kpis["total_fuel_kg"]), " kg")
    println("Benchmark fuel     = ", @sprintf("%.3f", benchmark_kpis["total_fuel_kg"]), " kg")
    println("Fuel delta         = ", @sprintf("%.3f", comparison["fuel_delta_g"] / 1000.0), " kg (", @sprintf("%.2f", comparison["fuel_delta_pct"]), " %)")
    println("Min up time       = ", rolling_settings.min_up_time_steps, " steps")
    println("Rolling starts     = ", rolling_kpis["generator_starts"])
    println("Benchmark starts   = ", benchmark_kpis["generator_starts"])
    println("Rolling min SOC    = ", @sprintf("%.2f", rolling_kpis["minimum_soc_pct"]), " %")
    println("Rolling final SOC  = ", @sprintf("%.2f", rolling_kpis["final_soc_pct"]), " %")
    if rolling_settings.soc_strategy == "soft_band"
        println("Realized low slack = ", @sprintf("%.3f", rolling_kpis["realized_total_soc_min_slack_kwh"]), " kWh")
        println("Realized high slack= ", @sprintf("%.3f", rolling_kpis["realized_total_soc_max_slack_kwh"]), " kWh")
        println("Local low slack    = ", @sprintf("%.3f", rolling_kpis["local_total_soc_min_slack_kwh"]), " kWh")
        println("Local high slack   = ", @sprintf("%.3f", rolling_kpis["local_total_soc_max_slack_kwh"]), " kWh")
        if rolling_settings.soft_band_terminal_reserve_enabled
            println("Terminal slack sum = ", @sprintf("%.3f", rolling_kpis["total_terminal_slack_kwh"]), " kWh")
            println("Terminal slack max = ", @sprintf("%.3f", rolling_kpis["maximum_terminal_slack_kwh"]), " kWh")
        end
    else
        println("Terminal slack sum = ", @sprintf("%.3f", rolling_kpis["total_terminal_slack_kwh"]), " kWh")
        println("Terminal slack max = ", @sprintf("%.3f", rolling_kpis["maximum_terminal_slack_kwh"]), " kWh")
    end
    println("Median solve time  = ", @sprintf("%.4f", rolling_kpis["median_solve_time_s"]), " s")
    println("P95 solve time     = ", @sprintf("%.4f", rolling_kpis["p95_solve_time_s"]), " s")
    println("Max solve time     = ", @sprintf("%.4f", rolling_kpis["maximum_solve_time_s"]), " s")
    println("Non-opt/timeout/infeasible local solves = ", rolling_kpis["nonoptimal_timeout_or_infeasible_solves"])
end

main()
