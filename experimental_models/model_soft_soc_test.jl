function build_model_soft_soc_test(gensets, load, battery, initial_commitment, soft_soc)
    model = Model(HiGHS.Optimizer)

    G = 1:length(gensets)
    T = 1:length(load)
    E_idx = 1:(length(load) + 1)

    # Generator variables
    @variable(model, u[g in G, t in T], Bin)
    @variable(model, 0 <= y[g in G, t in T] <= 1)
    @variable(model, Pg[g in G, t in T] >= 0)
    @variable(model, mdot[g in G, t in T] >= 0)
    @variable(model, 0 <= lambda[g in G, t in T, i in 1:length(gensets[g].SFOC)] <= 1)

    # Battery variables
    @variable(model, 0 <= P_ch[t in T] <= battery.P_ch_max)
    @variable(model, 0 <= P_dis[t in T] <= battery.P_dis_max)
    @variable(model, 0 <= E[e in E_idx] <= battery.E_max)
    @variable(model, z_bat[t in T], Bin)  # battery mode (1 if discharging, 0 if charging)
    @variable(model, soc_min_slack[e in E_idx] >= 0)
    @variable(model, soc_max_slack[e in E_idx] >= 0)

    soc_min_target = battery.SOC_min * battery.E_max
    soc_max_target = battery.SOC_max * battery.E_max

    @constraint(model, E[1] == battery.E_init)
    @constraint(model, [e in E_idx], soc_min_slack[e] >= soc_min_target - E[e])
    @constraint(model, [e in E_idx], soc_max_slack[e] >= E[e] - soc_max_target)
    @constraint(model, [t in T], P_dis[t] <= z_bat[t] * battery.P_dis_max)
    @constraint(model, [t in T], P_ch[t] <= (1 - z_bat[t]) * battery.P_ch_max)

    for t in T
        @constraint(model, sum(Pg[g, t] for g in G) + P_dis[t] - P_ch[t] == load[t])

        for g in G
            u_prev = (t == 1) ? initial_commitment[g] : u[g, t - 1]
            @constraint(model, y[g, t] >= u[g, t] - u_prev)
            @constraint(model, y[g, t] <= u[g, t])
            @constraint(model, y[g, t] <= 1 - u_prev)

            @constraint(model, Pg[g, t] >= gensets[g].P_min * u[g, t])
            @constraint(model, Pg[g, t] <= gensets[g].P_max * u[g, t])

            @constraint(model, sum(lambda[g, t, i] for i in 1:length(gensets[g].SFOC)) == u[g, t])
            @constraint(model, Pg[g, t] == sum(lambda[g, t, i] * gensets[g].P[i] for i in 1:length(gensets[g].SFOC)))
            @constraint(
                model,
                mdot[g, t] == sum(
                    lambda[g, t, i] * gensets[g].P[i] * gensets[g].SFOC[i]
                    for i in 1:length(gensets[g].SFOC)
                )
            )
            @constraint(model, [lambda[g, t, i] for i in 1:length(gensets[g].SFOC)] in SOS2())
        end

        for g in 1:(length(G) - 1)
            @constraint(model, Pg[g, t] >= Pg[g + 1, t])
        end

        @constraint(
            model,
            E[t + 1] == E[t] + battery.dt * (
                battery.eta_ch * P_ch[t] -
                (1.0 / battery.eta_dis) * P_dis[t]
            )
        )
    end

    @objective(
        model,
        Min,
        battery.dt * sum(mdot[g, t] for g in G, t in T) +
        sum(gensets[g].startup_cost * y[g, t] for g in G, t in T) +
        soft_soc.soc_min_penalty_g_per_kwh * sum(soc_min_slack[e] for e in E_idx) +
        soft_soc.soc_max_penalty_g_per_kwh * sum(soc_max_slack[e] for e in E_idx)
    )

    return model, u, y, Pg, mdot, lambda, P_ch, P_dis, E, soc_min_slack, soc_max_slack
end
