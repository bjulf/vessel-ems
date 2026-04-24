using JuMP, HiGHS, Printf, Dates, TOML

include("model_soft_soc_test.jl")
include(joinpath(@__DIR__, "..", "run_common.jl"))

const MOI = JuMP.MOI

solver_option(model, name) = Float64(MOI.get(backend(model), MOI.RawOptimizerAttribute(name)))

function extract_results(load, gensets, u, y, Pg, mdot, lambda, P_ch, P_dis, E, soc_min_slack, soc_max_slack)
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
        soc_min_slack = [value(soc_min_slack[t]) for t in 1:(length(load) + 1)],
        soc_max_slack = [value(soc_max_slack[t]) for t in 1:(length(load) + 1)],
    )
end

function load_soft_soc_settings(config_path)
    raw = TOML.parsefile(config_path)
    soft_soc_cfg = required_key(raw, "soft_soc", config_path)

    return (
        soc_min_penalty_g_per_kwh = Float64(required_key(soft_soc_cfg, "soc_min_penalty_g_per_kwh", "[soft_soc]")),
        soc_max_penalty_g_per_kwh = Float64(required_key(soft_soc_cfg, "soc_max_penalty_g_per_kwh", "[soft_soc]")),
    )
end

function soft_soc_metadata(battery, results, soft_soc)
    soc_min_target = battery.SOC_min * battery.E_max
    soc_max_target = battery.SOC_max * battery.E_max
    state_count = length(results.E)

    min_violation_steps = count(>(1e-9), results.soc_min_slack)
    max_violation_steps = count(>(1e-9), results.soc_max_slack)

    return Dict(
        "targets" => Dict(
            "soc_min_kwh" => soc_min_target,
            "soc_max_kwh" => soc_max_target,
            "soc_min_pct" => battery.SOC_min * 100.0,
            "soc_max_pct" => battery.SOC_max * 100.0,
        ),
        "penalties" => Dict(
            "soc_min_penalty_g_per_kwh" => soft_soc.soc_min_penalty_g_per_kwh,
            "soc_max_penalty_g_per_kwh" => soft_soc.soc_max_penalty_g_per_kwh,
        ),
        "violations" => Dict(
            "state_count" => state_count,
            "soc_min_violation_states" => min_violation_steps,
            "soc_max_violation_states" => max_violation_steps,
            "total_soc_min_violation_kwh" => sum(results.soc_min_slack),
            "total_soc_max_violation_kwh" => sum(results.soc_max_slack),
            "max_soc_min_violation_kwh" => maximum(results.soc_min_slack),
            "max_soc_max_violation_kwh" => maximum(results.soc_max_slack),
            "soc_min_penalty_g" => soft_soc.soc_min_penalty_g_per_kwh * sum(results.soc_min_slack),
            "soc_max_penalty_g" => soft_soc.soc_max_penalty_g_per_kwh * sum(results.soc_max_slack),
        ),
    )
end

function main()
    config_arg = isempty(ARGS) ? joinpath("config", "baseline_model_no_terminal_soft_soc.toml") : ARGS[1]
    config_path = resolve_repo_path(config_arg)
    cfg = load_model_config(config_path)
    soft_soc = load_soft_soc_settings(config_path)

    run_label = cfg.run_label
    run_desc = cfg.run_desc
    git_hash = strip(read(`git rev-parse HEAD`, String))
    git_dirty = !success(`git diff --quiet HEAD`)

    gensets = cfg.gensets
    battery = cfg.battery
    dt_minutes = cfg.dt_minutes
    load_profile_path = cfg.load_profile_path
    isfile(load_profile_path) || error(
        "Missing $(load_profile_path) referenced by $(config_path)."
    )
    load, datetimes = read_load_profile(load_profile_path)

    model, u, y, Pg, mdot, lambda, P_ch, P_dis, E, soc_min_slack, soc_max_slack = build_model_soft_soc_test(
        gensets,
        load,
        battery,
        cfg.initial_commitment,
        soft_soc,
    )

    if !cfg.show_solver_log
        set_silent(model)
    end

    optimize!(model)

    if termination_status(model) == OPTIMAL
        primal_tol = solver_option(model, "primal_feasibility_tolerance")
        mip_tol = solver_option(model, "mip_feasibility_tolerance")
        results = extract_results(load, gensets, u, y, Pg, mdot, lambda, P_ch, P_dis, E, soc_min_slack, soc_max_slack)

        timestamp = Dates.format(now(), "yyyy-mm-dd_HHMMSS")
        run_dir = joinpath(@__DIR__, "..", "runs", "$(timestamp)_$(run_label)")
        mkpath(run_dir)

        validation = validation_metadata(
            load,
            datetimes,
            battery,
            results.Pg,
            results.P_ch,
            results.P_dis,
            results.E;
            primal_tolerance = primal_tol,
            mip_tolerance = mip_tol,
            energy_tolerance = primal_tol,
        )
        soft_soc_summary = soft_soc_metadata(battery, results, soft_soc)

        params_dict = Dict(
            "run" => Dict(
                "date" => Dates.format(now(), "yyyy-mm-dd"),
                "label" => run_label,
                "description" => run_desc,
                "git_hash" => git_hash,
                "git_dirty" => git_dirty,
                "config_file" => config_path,
                "entry_point" => "experimental_models/main_soft_soc_test.jl",
                "model_file" => "experimental_models/model_soft_soc_test.jl",
            ),
            "solver" => Dict(
                "status" => string(termination_status(model)),
                "objective" => objective_value(model),
                "solve_time_s" => solve_time(model),
            ),
            "validation" => validation,
            "battery" => battery_energy_metadata(battery),
            "initial_conditions" => Dict(
                "generator_commitment" => collect(cfg.initial_commitment),
                "battery_energy_kwh" => battery.E_init,
            ),
            "terminal_conditions" => Dict(
                "battery_energy_min_kwh_reference" => battery.E_terminal_min,
                "constraint_enforced" => false,
            ),
            "soft_soc" => soft_soc_summary,
            "load_profile" => Dict(
                "source_file" => load_profile_path,
                "timesteps" => length(load),
                "start_datetime" => datetimes[1],
                "end_datetime" => datetimes[end],
                "dt_minutes" => dt_minutes,
            ),
            "generators" => [
                Dict(
                    "P_max" => g.P_max,
                    "P_min" => g.P_min,
                    "P" => collect(Float64, g.P),
                    "SFOC" => collect(Float64, g.SFOC),
                    "startup_cost" => g.startup_cost,
                )
                for g in gensets
            ],
        )
        open(joinpath(run_dir, "params.toml"), "w") do io
            TOML.print(io, params_dict)
        end

        csv_path = joinpath(run_dir, "dispatch_results.csv")
        write_results_csv(csv_path, load, datetimes, gensets, battery, results)

        open(joinpath(@__DIR__, "..", ".current_run"), "w") do io
            write(io, run_dir)
        end

        println("Objective value = ", @sprintf("%.2f", objective_value(model)))
        println("Solve time      = ", @sprintf("%.2f", solve_time(model)), " s")
        println("Min SOC slack   = ", @sprintf("%.3f", sum(results.soc_min_slack)), " kWh")
        println("Max SOC slack   = ", @sprintf("%.3f", sum(results.soc_max_slack)), " kWh")
        println("Final SOC       = ", @sprintf("%.2f", results.E[end] / battery.E_max * 100.0), " %")
        println("Run saved to    -> ", run_dir)
    else
        println("Model not solved to optimality.")
        println("  Termination status: ", termination_status(model))
        println("  Primal status:      ", primal_status(model))
    end
end

main()
