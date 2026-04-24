using JuMP, HiGHS, Printf, Dates, TOML

include("model_baseline_no_terminal_soc.jl")
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

function main()
    config_arg = isempty(ARGS) ? joinpath("config", "baseline_model_no_terminal_soc.toml") : ARGS[1]
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

    model, u, y, Pg, mdot, lambda, P_ch, P_dis, E = build_model_baseline_no_terminal_soc(
        gensets,
        load,
        battery,
        cfg.initial_commitment,
    )

    if !show_solver_log
        set_silent(model)
    end

    optimize!(model)

    if termination_status(model) == OPTIMAL
        primal_tol = solver_option(model, "primal_feasibility_tolerance")
        mip_tol = solver_option(model, "mip_feasibility_tolerance")
        results = extract_results(load, gensets, u, y, Pg, mdot, lambda, P_ch, P_dis, E)

        timestamp = Dates.format(now(), "yyyy-mm-dd_HHMMSS")
        run_dir = joinpath(@__DIR__, "runs", "$(timestamp)_$(run_label)")
        mkpath(run_dir)

        validation = validation_metadata(
            load,
            datetimes,
            battery,
            results.Pg,
            results.P_ch,
            results.P_dis,
            results.E;
            primal_tolerance=primal_tol,
            mip_tolerance=mip_tol,
            energy_tolerance=primal_tol,
        )

        params_dict = Dict(
            "run" => Dict(
                "date"        => Dates.format(now(), "yyyy-mm-dd"),
                "label"       => run_label,
                "description" => run_desc,
                "git_hash"    => git_hash,
                "git_dirty"   => git_dirty,
                "config_file" => config_path,
                "entry_point" => "main_baseline_no_terminal_soc.jl",
                "model_file"  => "model_baseline_no_terminal_soc.jl",
            ),
            "solver" => Dict(
                "status"       => string(termination_status(model)),
                "objective"    => objective_value(model),
                "solve_time_s" => solve_time(model),
            ),
            "validation" => validation,
            "battery" => battery_energy_metadata(battery),
            "initial_conditions" => Dict(
                "generator_commitment" => collect(cfg.initial_commitment),
                "battery_energy_kwh"   => battery.E_init,
            ),
            "terminal_conditions" => Dict(
                "battery_energy_min_kwh_reference" => battery.E_terminal_min,
                "constraint_enforced"              => false,
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
        write_results_csv(csv_path, load, datetimes, gensets, battery, results)

        open(joinpath(@__DIR__, ".current_run"), "w") do io
            write(io, run_dir)
        end

        println("Objective value = ", @sprintf("%.2f", objective_value(model)))
        println("Solve time      = ", @sprintf("%.2f", solve_time(model)), " s")
        println("Final SOC       = ", @sprintf("%.2f", results.E[end] / battery.E_max * 100.0), " %")
        println("Run saved to    -> ", run_dir)
    else
        println("Model not solved to optimality.")
        println("  Termination status: ", termination_status(model))
        println("  Primal status:      ", primal_status(model))
    end
end

main()
