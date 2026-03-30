using Statistics, TOML

function compute_metrics(run_dir)
    params        = TOML.parsefile(joinpath(run_dir, "params.toml"))
    dt_h          = params["battery"]["dt"]
    startup_cost  = params["generators"][1]["startup_cost"]
    solver_status = params["solver"]["status"]
    objective_g   = params["solver"]["objective"]
    solve_time_s  = params["solver"]["solve_time_s"]

    rows   = readlines(joinpath(run_dir, "dispatch_results.csv"))
    header = split(rows[1], ",")
    col    = Dict(strip(h) => i for (i, h) in enumerate(header))

    fuel_gph_total = 0.0
    total_startups = 0
    seen_timesteps = Dict{Int, @NamedTuple{P_ch_kw::Float64, P_dis_kw::Float64, soc_pct::Float64}}()

    for row in rows[2:end]
        isempty(strip(row)) && continue
        v = split(row, ",")
        t        = parse(Int,     v[col["timestep"]])
        startup  = parse(Float64, v[col["startup"]])
        fuel_gph = parse(Float64, v[col["fuel_gph"]])
        fuel_gph_total += fuel_gph
        total_startups += startup > 0.5 ? 1 : 0
        if !haskey(seen_timesteps, t)
            seen_timesteps[t] = (
                P_ch_kw  = parse(Float64, v[col["P_ch_kw"]]),
                P_dis_kw = parse(Float64, v[col["P_dis_kw"]]),
                soc_pct  = parse(Float64, v[col["soc_pct"]]),
            )
        end
    end

    fuel_cost_g            = fuel_gph_total * dt_h
    startup_cost_g         = total_startups * startup_cost
    battery_throughput_kwh = sum(r.P_ch_kw + r.P_dis_kw for r in values(seen_timesteps)) * dt_h
    soc_values             = [r.soc_pct for r in values(seen_timesteps)]
    mean_soc_pct           = mean(soc_values)
    final_soc_pct          = seen_timesteps[maximum(keys(seen_timesteps))].soc_pct
    min_soc_pct            = minimum(soc_values)

    return (;
        solver_status,
        objective_g,
        fuel_cost_g,
        startup_cost_g,
        battery_throughput_kwh,
        mean_soc_pct,
        final_soc_pct,
        min_soc_pct,
        solve_time_s,
    )
end

function is_valid_run(m)
    m.solver_status == "OPTIMAL" || return false
    isfinite(m.objective_g)      || return false
    m.objective_g > 0            || return false
    m.fuel_cost_g > 0            || return false
    m.min_soc_pct >= 19.0        || return false
    return true
end
