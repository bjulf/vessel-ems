using JuMP, HiGHS, Printf, Dates, TOML

include("model.jl")

format_num(x) = @sprintf("%.6f", isapprox(x, 0.0; atol=1e-9) ? 0.0 : x)

function write_results_csv(path, load, gensets, battery, u, Pg, SFOC, lambda, P_ch, P_dis, E)
    max_breakpoints = maximum(length(g.SFOC) for g in gensets)

    open(path, "w") do io
        header = ["timestep", "generator", "load_kw", "u", "Pg_kw",
                  "sfoc_gkwh", "fuel_gph", "load_pct",
                  "P_ch_kw", "P_dis_kw", "E_kwh", "soc_pct"]
        append!(header, ["lambda_$(i)" for i in 1:max_breakpoints])
        println(io, join(header, ","))

        for t in eachindex(load), g in eachindex(gensets)
            pg_val  = value(Pg[g, t])
            fg_val  = value(SFOC[g, t])
            pg_val  = isapprox(pg_val, 0.0; atol=1e-9) ? 0.0 : pg_val
            fg_val  = isapprox(fg_val, 0.0; atol=1e-9) ? 0.0 : fg_val
            fuel    = fg_val * pg_val          # g/h  (sfoc × power)
            loadpct = pg_val / gensets[g].P_max * 100.0  # % of rated capacity

            # Battery values (same for all generators in a timestep)
            pch_val  = isapprox(value(P_ch[t]), 0.0; atol=1e-9) ? 0.0 : value(P_ch[t])
            pdis_val = isapprox(value(P_dis[t]), 0.0; atol=1e-9) ? 0.0 : value(P_dis[t])
            e_val    = value(E[t])
            soc_val  = e_val / battery.E_max * 100.0

            row = [
                string(t),
                string(g),
                @sprintf("%.1f", load[t]),
                value(u[g, t]) > 0.5 ? "1" : "0",
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

function main()
    # ── Run identity ───────────────────────────────────────────────────────────
    # Set run_label before each run — it becomes part of the folder name.
    # Fill run_desc with a short note about what you're testing (optional).
    run_label = "Test"
    run_desc  = "Initial test run of quarto report setup with 2 gensets and 4-day load profile."

    git_hash  = strip(read(`git rev-parse HEAD`, String))
    git_dirty = !success(`git diff --quiet HEAD`)

    gensets = [
        (P_max=385.0, P_min=0.5*385, P = [0.5*385, 0.75*385, 310, 385], SFOC = [193,191,191,198]),
        (P_max=385.0, P_min=0.5*385, P = [0.5*385, 0.75*385, 310, 385], SFOC = [193,191,191,198])
    ]

    battery = (
        E_max     = 940.0,    # kWh  total battery capacity
        SOC_min   = 0.2,      #      minimum state of charge
        SOC_max   = 0.9,      #      maximum state of charge
        P_ch_max  = 100.0,    # kW   max charging power
        P_dis_max = 100.0,    # kW   max discharging power
        eta_ch    = 0.95,     #      charging efficiency
        eta_dis   = 0.95,     #      discharging efficiency
        E_init    = 0.5*940,  # kWh  initial stored energy (50% SOC)
        dt        = 1.0,      # h    timestep duration
        SOC_ref   = 0.35,      #      SOC reference target (35%)
        soc_penalty = 10.0,    #      penalty weight λ for |SOC_t - SOC_ref| deviation
    )

    # Load profile over 100-hour time horizon (~4 days), values in kW
    load = [
        # Day 1 – hours 1-24
        280.0, 260.0, 250.0, 245.0, 250.0, 270.0,   # 01-06 night/early morning
        320.0, 390.0, 470.0, 530.0, 580.0, 610.0,   # 07-12 morning ramp-up
        620.0, 600.0, 590.0, 570.0, 560.0, 530.0,   # 13-18 afternoon
        500.0, 460.0, 430.0, 400.0, 360.0, 70.0,   # 19-24 evening wind-down
        # Day 2 – hours 25-48
        60.0, 50.0, 150.0, 150.0, 150.0, 170.0,   # 01-06
        315.0, 385.0, 465.0, 525.0, 575.0, 605.0,   # 07-12
        615.0, 595.0, 585.0, 565.0, 555.0, 525.0,   # 13-18
        495.0, 455.0, 425.0, 395.0, 355.0, 305.0,   # 19-24
        # Day 3 – hours 49-72  (higher load, e.g. increased activity)
        290.0, 270.0, 260.0, 255.0, 262.0, 280.0,   # 01-06
        340.0, 410.0, 490.0, 550.0, 600.0, 630.0,   # 07-12
        640.0, 625.0, 610.0, 595.0, 580.0, 550.0,   # 13-18
        515.0, 475.0, 445.0, 415.0, 375.0, 325.0,   # 19-24
        # Day 4 – hours 73-96  (tapering back down)
        270.0, 252.0, 244.0, 240.0, 246.0, 262.0,   # 01-06
        308.0, 375.0, 452.0, 512.0, 558.0, 588.0,   # 07-12
        595.0, 578.0, 568.0, 550.0, 540.0, 512.0,   # 13-18
        482.0, 445.0, 415.0, 385.0, 348.0, 298.0,   # 19-24
        # Hours 97-100 (start of day 5)
        268.0, 250.0, 242.0, 238.0,
    ]

    show_solver_log = true

    model, u, Pg, SFOC, lambda, P_ch, P_dis, E, soc_dev = build_model(gensets, load, battery)

    if !show_solver_log
        set_silent(model)
    end

    optimize!(model)

    if termination_status(model) == OPTIMAL
        # ── Create run directory ───────────────────────────────────────────────
        timestamp = Dates.format(now(), "yyyy-mm-dd_HHMMSS")
        run_dir   = joinpath(@__DIR__, "runs", "$(timestamp)_$(run_label)")
        mkpath(run_dir)

        # ── Write params.toml ──────────────────────────────────────────────────
        params_dict = Dict(
            "run" => Dict(
                "date"        => Dates.format(now(), "yyyy-mm-dd"),
                "label"       => run_label,
                "description" => run_desc,
                "git_hash"    => git_hash,
                "git_dirty"   => git_dirty,
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
                "SOC_ref"     => battery.SOC_ref,
                "soc_penalty" => battery.soc_penalty,
            ),
            "generators" => [
                Dict(
                    "P_max" => g.P_max,
                    "P_min" => g.P_min,
                    "P"     => collect(Float64, g.P),
                    "SFOC"  => collect(Float64, g.SFOC),
                )
                for g in gensets
            ],
        )
        open(joinpath(run_dir, "params.toml"), "w") do io
            TOML.print(io, params_dict)
        end

        # ── Write results CSV ──────────────────────────────────────────────────
        csv_path = joinpath(run_dir, "dispatch_results.csv")
        write_results_csv(csv_path, load, gensets, battery, u, Pg, SFOC, lambda, P_ch, P_dis, E)

        # Write .current_run so report.qmd picks it up without env vars
        open(joinpath(@__DIR__, ".current_run"), "w") do io
            write(io, run_dir)
        end

        println("Objective value = ", @sprintf("%.2f", objective_value(model)))
        println("Solve time      = ", @sprintf("%.2f", solve_time(model)), " s")
        println("Run saved to    → ", run_dir)
    else
        println("Model not solved to optimality.")
        println("  Termination status: ", termination_status(model))
        println("  Primal status:      ", primal_status(model))
    end
end

main()