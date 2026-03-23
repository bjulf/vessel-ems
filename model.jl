
function build_model(gensets, load, battery)
    model = Model(HiGHS.Optimizer)

    G = 1:length(gensets)
    T = 1:length(load)

    # ── Generator variables ────────────────────────────────────────────────
    @variable(model, u[g in G, t in T], Bin)                                      # on/off status
    @variable(model, 0 <= y[g in G, t in T] <= 1)                                 # startup event (1 if g starts at t); continuous — integrality of u forces 0/1 at optimum
    @variable(model, Pg[g in G, t in T] >= 0)                                     # power output
    @variable(model, SFOC[g in G, t in T] >= 0)                                     # specific fuel oil consumption (g/kWh)
    @variable(model, 0 <= lambda[g in G, t in T, i in 1:length(gensets[g].SFOC)] <= 1)

    # ── Battery variables ──────────────────────────────────────────────────
    @variable(model, 0 <= P_ch[t in T]  <= battery.P_ch_max)                      # charging power
    @variable(model, 0 <= P_dis[t in T] <= battery.P_dis_max)                     # discharging power
    @variable(model, battery.SOC_min * battery.E_max <= E[t in 1:length(load)+1] <= battery.SOC_max * battery.E_max)  # stored energy
    @variable(model, z_bat[t in T], Bin)                                             # battery charge/discharge status (1 if charging, 0 if discharging)
    @variable(model, soc_dev[t in T] >= 0)                                           # |SOC_t - SOC_ref| linearisation auxiliary

    # ── Initial energy state ───────────────────────────────────────────────
    @constraint(model, E[1] == battery.E_init)

    # ── Terminal SOC constraint: don't drain below reference at end of horizon
    @constraint(model, E[length(T)+1] >= battery.E_init)

    for t in T
        # Power balance: generators + battery discharge − battery charge = load
        @constraint(model, sum(Pg[g, t] for g in G) + P_dis[t] - P_ch[t] == load[t])

        # ── Generator constraints ──────────────────────────────────────────
        for g in G
            # Startup indicator: y[g,t] = 1 iff unit transitions off→on at t.
            # u_prev = 0 for t=1 (all units assumed offline before horizon).
            u_prev = (t == 1) ? 0 : u[g, t-1]
            @constraint(model, y[g, t] >= u[g, t] - u_prev)   # force y=1 on off→on transition
            @constraint(model, y[g, t] <= u[g, t])             # y=0 if unit is currently off
            @constraint(model, y[g, t] <= 1 - u_prev)          # y=0 if unit was already running

            @constraint(model, Pg[g, t] >= gensets[g].P_min * u[g, t])
            @constraint(model, Pg[g, t] <= gensets[g].P_max * u[g, t])

            @constraint(model, sum(lambda[g, t, i] for i in 1:length(gensets[g].SFOC)) == u[g, t])

            @constraint(model, Pg[g, t] == sum(lambda[g, t, i] * gensets[g].P[i] for i in 1:length(gensets[g].SFOC)))

            @constraint(model, SFOC[g, t] == sum(lambda[g, t, i] * gensets[g].SFOC[i] for i in 1:length(gensets[g].SFOC)))

            @constraint(model, [lambda[g, t, i] for i in 1:length(gensets[g].SFOC)] in SOS2())
        end

        # Symmetry-breaking: enforce ordering on identical generators per time step
        for g in 1:(length(G)-1)
            @constraint(model, Pg[g, t] >= Pg[g+1, t])
        end
        
        # ── Battery constraints ─────────────────────────────────────────────
        @constraint(model, [t in T], P_dis[t] <= z_bat[t] * battery.P_dis_max)
        @constraint(model, [t in T], P_ch[t]  <= (1 - z_bat[t]) * battery.P_ch_max)

        # Battery energy evolution
        # E_{k+1} = E_k + Δt (η_ch · P_ch_k − (1/η_dis) · P_dis_k)
        @constraint(model,
            E[t+1] == E[t] + battery.dt * (
                battery.eta_ch  * P_ch[t] -
                (1.0 / battery.eta_dis) * P_dis[t]
            )
        )

        # SOC deviation linearisation: soc_dev[t] >= |SOC_t - SOC_ref|
        @constraint(model, soc_dev[t] >= E[t] / battery.E_max - battery.SOC_ref)
        @constraint(model, soc_dev[t] >= battery.SOC_ref - E[t] / battery.E_max)
    end

    # ── Objective: minimise total fuel flow + startup cost + SOC deviation penalty ─────────
    @objective(model, Min,
        sum(lambda[g, t, i] * gensets[g].SFOC[i] * gensets[g].P[i]
            for g in G, t in T, i in 1:length(gensets[g].SFOC)) +
        sum(gensets[g].startup_cost * y[g, t] for g in G, t in T) +
        battery.soc_penalty * sum(soc_dev[t] for t in T)
    )
    

    return model, u, y, Pg, SFOC, lambda, P_ch, P_dis, E, soc_dev
end


#Hmm må vurdere hvorvidt jeg trenger spenningsgrenser på DClink etc..7

