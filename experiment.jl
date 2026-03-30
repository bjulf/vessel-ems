using Dates, Printf

include("main.jl")
include("metrics.jl")

# ── Candidate grid ─────────────────────────────────────────────────────────────
E_MAX             = 940.0
E_init_soc_values = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
MODEL_VARIANT     = "baseline"

# ── History file ───────────────────────────────────────────────────────────────
HISTORY_FILE = joinpath(@__DIR__, "experiments", "history.csv")
mkpath(dirname(HISTORY_FILE))

HISTORY_HEADER = join([
    "run_id", "timestamp", "model_variant", "E_init_soc", "E_init_kwh",
    "solver_status", "objective_g", "fuel_cost_g", "startup_cost_g",
    "battery_throughput_kwh", "mean_soc_pct", "final_soc_pct", "min_soc_pct",
    "solve_time_s", "run_dir",
], ",")

if !isfile(HISTORY_FILE)
    open(HISTORY_FILE, "w") do io; println(io, HISTORY_HEADER); end
end

# ── Run loop ───────────────────────────────────────────────────────────────────
n = length(E_init_soc_values)
for (i, soc) in enumerate(E_init_soc_values)
    e_init = soc * E_MAX
    println("\n[$i/$n] E_init = $(round(soc*100, digits=0))% SOC  ($(e_init) kWh)")

    cfg = default_config()
    cfg = merge(cfg, (
        battery         = merge(cfg.battery, (E_init = e_init,)),
        label           = "einit_$(round(Int, soc * 100))",
        model_variant   = MODEL_VARIANT,
        show_solver_log = false,
    ))

    run_dir = nothing
    m       = nothing
    status  = "ERROR"
    notes   = ""

    try
        run_dir = main(cfg)
        if run_dir !== nothing
            m      = compute_metrics(run_dir)
            status = m.solver_status
            if !is_valid_run(m)
                notes = "invalid"
                @warn "Run flagged invalid" run_dir
            end
        else
            status = "INFEASIBLE"
        end
    catch e
        status = "ERROR"
        notes  = replace(sprint(showerror, e), "\n" => " ")
        @warn "Run threw an exception" exception=e
    end

    run_id    = countlines(HISTORY_FILE)   # 1-indexed: header = line 1, first run = 1
    timestamp = Dates.format(now(), "yyyy-mm-dd HH:MM:SS")

    row = if m !== nothing
        [run_id, timestamp, MODEL_VARIANT, soc, e_init,
         m.solver_status, m.objective_g, m.fuel_cost_g, m.startup_cost_g,
         m.battery_throughput_kwh, m.mean_soc_pct, m.final_soc_pct, m.min_soc_pct,
         m.solve_time_s, something(run_dir, "")]
    else
        [run_id, timestamp, MODEL_VARIANT, soc, e_init,
         status, NaN, NaN, NaN, NaN, NaN, NaN, NaN, NaN, ""]
    end

    open(HISTORY_FILE, "a") do io; println(io, join(row, ",")); end
end

# ── Ranked summary ─────────────────────────────────────────────────────────────
println("\n", "="^72)
println("RESULTS — ranked by objective (fuel + startup cost, grams)")
println("="^72)
println(@sprintf("%-4s  %-10s  %-14s  %-14s  %-14s  %-12s",
    "#", "E_init_soc", "objective_g", "fuel_cost_g", "startup_g", "batt_kwh"))
println("-"^72)

lines = readlines(HISTORY_FILE)
rows  = [split(l, ",") for l in lines[2:end] if !isempty(strip(l))]
valid = filter(r -> r[6] == "OPTIMAL", rows)
sort!(valid, by = r -> parse(Float64, r[7]))

for (rank, r) in enumerate(valid)
    soc_pct  = round(parse(Float64, r[4]) * 100, digits=0)
    obj      = parse(Float64, r[7])
    fuel     = parse(Float64, r[8])
    startup  = parse(Float64, r[9])
    batt     = parse(Float64, r[10])
    println(@sprintf("%-4d  %-10s  %-14.0f  %-14.0f  %-14.0f  %-12.1f",
        rank, "$(soc_pct)%", obj, fuel, startup, batt))
end

println("="^72)
println("History saved to: ", HISTORY_FILE)
