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
    run_label = "Initial run"
    run_desc  = "4-day profile with low-demand port/anchorage stretches (0-100 kW) and peaks up to 700 kW. Initial run."
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
        P_ch_max  = 753.25,   # kW  nominal max charging power (655V*1150A)
        P_dis_max = 943.2,    # kW   mominal discharging power (655V*1440A)
        eta_ch    = 0.95,     #      charging efficiency
        eta_dis   = 0.95,     #      discharging efficiency
        E_init    = 0.5*940,  # kWh  initial stored energy (50% SOC)
        dt        = 1.0,      # h    timestep duration
        SOC_ref   = 0.8,      #      SOC reference target 
        soc_penalty = 10.0,    #      penalty weight λ for |SOC_t - SOC_ref| deviation
    )

    # Load profile over 100-hour time horizon (~4 days), values in kW
    # Includes at-sea high-load periods (up to 700 kW), normal transit, and
    # low-demand stretches (0–100 kW) representing port/anchorage or hotel load.
    load = [
        # Day 1 – at sea, moderate-to-high load
        280.0, 260.0, 250.0, 245.0, 250.0, 270.0,   # 01-06 night transit
        340.0, 430.0, 530.0, 610.0, 670.0, 695.0,   # 07-12 morning ramp-up (peak ~700 kW)
        700.0, 680.0, 660.0, 635.0, 610.0, 570.0,   # 13-18 afternoon high load
        530.0, 480.0, 440.0, 390.0, 340.0, 290.0,   # 19-24 evening wind-down
        # Day 2 – arrival and port stay (very low load)
        240.0, 190.0,  80.0,  50.0,  40.0,  35.0,   # 01-06 arrival, engines shutting down
         30.0,  45.0,  60.0,  75.0,  85.0,  90.0,   # 07-12 hotel load at berth
         95.0,  90.0,  85.0,  80.0,  70.0,  60.0,   # 13-18 port stay
         55.0,  50.0,  45.0, 550.0, 50.0, 60.0,   # 19-24 departure prep and manoeuvring
        # Day 3 – at sea, high activity (peak load day)
        40.0, 275.0, 265.0, 258.0, 265.0, 285.0,   # 01-06 night transit
        360.0, 445.0, 545.0, 620.0, 675.0, 698.0,   # 07-12 morning ramp-up
        700.0, 685.0, 670.0, 650.0, 625.0, 590.0,   # 13-18 peak transit load
        550.0, 505.0, 465.0, 425.0, 375.0, 320.0,   # 19-24 evening
        # Day 4 – mixed: morning transit, afternoon anchorage
        275.0, 255.0, 246.0, 242.0, 248.0, 265.0,   # 01-06 night transit
        315.0, 400.0, 490.0, 570.0, 620.0, 645.0,   # 07-12 morning
        580.0, 480.0, 350.0,  95.0,  65.0,  50.0,   # 13-18 anchor at 15:00 (load drops)
         45.0,  40.0,  38.0,  42.0,  55.0,  75.0,   # 19-24 overnight at anchor
        # Hours 97-100 (weigh anchor, restart transit)
        110.0, 195.0, 270.0, 340.0,
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