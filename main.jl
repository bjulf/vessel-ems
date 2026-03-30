using JuMP, HiGHS, Printf, Dates, TOML

include("model.jl")

format_num(x) = @sprintf("%.6f", isapprox(x, 0.0; atol=1e-9) ? 0.0 : x)

function write_results_csv(path, load, gensets, battery, u, y, Pg, SFOC, lambda, P_ch, P_dis, E)
    max_breakpoints = maximum(length(g.SFOC) for g in gensets)

    open(path, "w") do io
        header = ["timestep", "generator", "load_kw", "u", "startup",
                  "Pg_kw", "sfoc_gkwh", "fuel_gph", "load_pct",
                  "P_ch_kw", "P_dis_kw", "E_kwh", "soc_pct"]
        append!(header, ["lambda_$(i)" for i in 1:max_breakpoints])
        println(io, join(header, ","))

        for t in eachindex(load), g in eachindex(gensets)
            pg_val  = value(Pg[g, t])
            fg_val  = value(SFOC[g, t])
            pg_val  = isapprox(pg_val, 0.0; atol=1e-9) ? 0.0 : pg_val
            fg_val  = isapprox(fg_val, 0.0; atol=1e-9) ? 0.0 : fg_val
            fuel    = fg_val * pg_val
            loadpct = pg_val / gensets[g].P_max * 100.0

            pch_val  = isapprox(value(P_ch[t]), 0.0; atol=1e-9) ? 0.0 : value(P_ch[t])
            pdis_val = isapprox(value(P_dis[t]), 0.0; atol=1e-9) ? 0.0 : value(P_dis[t])
            e_val    = value(E[t])
            soc_val  = e_val / battery.E_max * 100.0

            row = [
                string(t),
                string(g),
                @sprintf("%.1f", load[t]),
                value(u[g, t]) > 0.5 ? "1" : "0",
                value(y[g, t]) > 0.5 ? "1" : "0",
                format_num(pg_val),
                format_num(fg_val),
                format_num(fuel),
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

function default_config()
    dt = 15 / 60.0
    gensets = [
        (P_max=385.0, P_min=0.5*385, P=[0.5*385, 0.75*385, 310, 385], SFOC=[193,191,191,198], startup_cost=15000.0),
        (P_max=385.0, P_min=0.5*385, P=[0.5*385, 0.75*385, 310, 385], SFOC=[193,191,191,198], startup_cost=15000.0),
    ]
    battery = (
        E_max     = 940.0,
        SOC_min   = 0.2,
        SOC_max   = 0.9,
        P_ch_max  = 753.25,
        P_dis_max = 943.2,
        eta_ch    = 0.95,
        eta_dis   = 0.95,
        E_init    = 0.5 * 940.0,
        dt        = dt,
    )
    return (
        gensets         = gensets,
        battery         = battery,
        label           = "",
        description     = "",
        show_solver_log = true,
        model_variant   = "baseline",
        objective       = (terms = ["fuel", "startup"],),
        constraints     = (terminal_soc = "gte_init",),
    )
end

function main(config=default_config())
    git_hash  = strip(read(`git rev-parse HEAD`, String))
    git_dirty = !success(`git diff --quiet HEAD`)

    gensets = config.gensets
    battery = config.battery

    load = Float64[]
    open(joinpath(@__DIR__, "data", "load_profile.csv")) do io
        readline(io)
        for line in eachline(io)
            parts = split(line, ",")
            push!(load, parse(Float64, parts[2]))
        end
    end

    model, u, y, Pg, SFOC, lambda, P_ch, P_dis, E = build_model(gensets, load, battery)

    if !config.show_solver_log
        set_silent(model)
    end

    optimize!(model)

    if termination_status(model) == OPTIMAL
        timestamp = Dates.format(now(), "yyyy-mm-dd_HHMMSS")
        run_dir   = joinpath(@__DIR__, "runs", "$(timestamp)_$(config.label)")
        mkpath(run_dir)

        params_dict = Dict(
            "run" => Dict(
                "date"          => Dates.format(now(), "yyyy-mm-dd"),
                "label"         => config.label,
                "description"   => config.description,
                "model_variant" => config.model_variant,
                "git_hash"      => git_hash,
                "git_dirty"     => git_dirty,
            ),
            "solver" => Dict(
                "status"       => string(termination_status(model)),
                "objective"    => objective_value(model),
                "solve_time_s" => solve_time(model),
            ),
            "objective" => Dict(
                "terms" => collect(config.objective.terms),
            ),
            "constraints" => Dict(
                "terminal_soc" => config.constraints.terminal_soc,
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
        write_results_csv(csv_path, load, gensets, battery, u, y, Pg, SFOC, lambda, P_ch, P_dis, E)

        open(joinpath(@__DIR__, ".current_run"), "w") do io
            write(io, run_dir)
        end

        println("Objective value = ", @sprintf("%.2f", objective_value(model)))
        println("Solve time      = ", @sprintf("%.2f", solve_time(model)), " s")
        println("Run saved to    → ", run_dir)

        return run_dir
    else
        println("Model not solved to optimality.")
        println("  Termination status: ", termination_status(model))
        println("  Primal status:      ", primal_status(model))
        return nothing
    end
end

if abspath(PROGRAM_FILE) == @__FILE__
    main()
end
