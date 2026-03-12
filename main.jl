using JuMP, HiGHS, Printf

include("model.jl")

format_num(x) = @sprintf("%.6f", isapprox(x, 0.0; atol=1e-9) ? 0.0 : x)

function write_results_csv(path, load, gensets, u, Pg, Fg, lambda)
    max_breakpoints = maximum(length(g.Fbp) for g in gensets)

    open(path, "w") do io
        header = ["timestep", "generator", "load_mw", "u", "Pg_mw",
                  "sfoc_gkwh", "fuel_gph", "load_pct"]
        append!(header, ["lambda_$(i)" for i in 1:max_breakpoints])
        println(io, join(header, ","))

        for t in eachindex(load), g in eachindex(gensets)
            pg_val  = value(Pg[g, t])
            fg_val  = value(Fg[g, t])
            pg_val  = isapprox(pg_val, 0.0; atol=1e-9) ? 0.0 : pg_val
            fg_val  = isapprox(fg_val, 0.0; atol=1e-9) ? 0.0 : fg_val
            fuel    = fg_val * pg_val          # g/h  (sfoc × power)
            loadpct = pg_val / gensets[g].P_max * 100.0  # % of rated capacity

            row = [
                string(t),
                string(g),
                @sprintf("%.1f", load[t]),
                value(u[g, t]) > 0.5 ? "1" : "0",
                format_num(pg_val),
                format_num(fg_val),
                format_num(fuel),
                @sprintf("%.2f", loadpct),
            ]

            for i in 1:max_breakpoints
                if i <= length(gensets[g].Fbp)
                    push!(row, format_num(value(lambda[g, t, i])))
                else
                    push!(row, "")
                end
            end

            println(io, join(row, ","))
        end
    end
end

function main()
    gensets = [
        (P_max=385.0, P_min=0.5*385, P = [0.5*385, 0.75*385, 310, 385], Fbp = [193,191,191,198]),
        (P_max=385.0, P_min=0.5*385, P = [0.5*385, 0.75*385, 310, 385], Fbp = [193,191,191,198])
    ]

    # Load profile over time horizon (e.g. 6 time steps)
    load = [300.0, 400.0, 500.0, 600.0, 450.0, 350.0]

    show_solver_log = true

    model, u, Pg, Fg, lambda = build_model(gensets, load)

    if !show_solver_log
        set_silent(model)
    end

    optimize!(model)

    if termination_status(model) == OPTIMAL
        output_path = joinpath(@__DIR__, "dispatch_results.csv")
        write_results_csv(output_path, load, gensets, u, Pg, Fg, lambda)

        println("Objective value = ", @sprintf("%.2f", objective_value(model)))
        println("Dispatch data written to ", output_path)
    else
        println("Model not solved to optimality.")
        println("  Termination status: ", termination_status(model))
        println("  Primal status:      ", primal_status(model))
    end
end

main()