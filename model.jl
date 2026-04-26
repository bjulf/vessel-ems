# Shared JuMP dispatch formulation and model wrappers.
#
# The global/full-horizon MILP and the rolling-horizon local MILP use the same
# physical dispatch core. The wrappers below only decide horizon-specific
# terminal treatment and objective additions.

function build_dispatch_model_core(
    gensets,
    load,
    battery,
    initial_commitment;
    energy_lower_kwh=battery.SOC_min * battery.E_max,
    energy_upper_kwh=battery.SOC_max * battery.E_max,
)
    model = Model(HiGHS.Optimizer)

    G = 1:length(gensets)
    T = 1:length(load)

    # Generator variables
    @variable(model, u[g in G, t in T], Bin)
    @variable(model, 0 <= y[g in G, t in T] <= 1)
    @variable(model, Pg[g in G, t in T] >= 0)
    @variable(model, mdot[g in G, t in T] >= 0)
    @variable(model, 0 <= lambda[g in G, t in T, i in 1:length(gensets[g].SFOC)] <= 1)

    # Battery variables
    @variable(model, 0 <= P_ch[t in T] <= battery.P_ch_max)
    @variable(model, 0 <= P_dis[t in T] <= battery.P_dis_max)
    @variable(
        model,
        energy_lower_kwh <= E[t in 1:(length(load) + 1)] <= energy_upper_kwh
    )
    @variable(model, z_bat[t in T], Bin)

    @constraint(model, E[1] == battery.E_init)
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
            @constraint(
                model,
                Pg[g, t] == sum(
                    lambda[g, t, i] * gensets[g].P[i]
                    for i in 1:length(gensets[g].SFOC)
                )
            )
            @constraint(
                model,
                mdot[g, t] == sum(
                    lambda[g, t, i] * gensets[g].P[i] * gensets[g].SFOC[i]
                    for i in 1:length(gensets[g].SFOC)
                )
            )
            @constraint(model, [lambda[g, t, i] for i in 1:length(gensets[g].SFOC)] in SOS2())
        end

        # Symmetry breaking for identical generators.
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

    @expression(
        model,
        fuel_startup_objective,
        battery.dt * sum(mdot[g, t] for g in G, t in T) +
        sum(gensets[g].startup_cost * y[g, t] for g in G, t in T)
    )

    return (
        model = model,
        u = u,
        y = y,
        Pg = Pg,
        mdot = mdot,
        lambda = lambda,
        P_ch = P_ch,
        P_dis = P_dis,
        E = E,
        fuel_startup_objective = fuel_startup_objective,
    )
end

function build_rolling_horizon_soft_soc_milp(
    gensets,
    forecast_load,
    battery,
    previous_commitment,
    preferred_soc_min,
    preferred_soc_max,
    soc_min_penalty,
    soc_max_penalty,
)
    components = build_dispatch_model_core(
        gensets,
        forecast_load,
        battery,
        previous_commitment;
        energy_lower_kwh=0.0,
        energy_upper_kwh=battery.E_max,
    )
    E_idx = 1:(length(forecast_load) + 1)
    preferred_e_min = preferred_soc_min * battery.E_max
    preferred_e_max = preferred_soc_max * battery.E_max

    @variable(components.model, soc_min_slack[e in E_idx] >= 0)
    @variable(components.model, soc_max_slack[e in E_idx] >= 0)
    @constraint(components.model, [e in E_idx], components.E[e] + soc_min_slack[e] >= preferred_e_min)
    @constraint(components.model, [e in E_idx], components.E[e] - soc_max_slack[e] <= preferred_e_max)
    @objective(
        components.model,
        Min,
        components.fuel_startup_objective +
        soc_min_penalty * sum(soc_min_slack[e] for e in E_idx) +
        soc_max_penalty * sum(soc_max_slack[e] for e in E_idx)
    )

    return merge(
        components,
        (
            soc_min_slack = soc_min_slack,
            soc_max_slack = soc_max_slack,
            preferred_soc_min = preferred_soc_min,
            preferred_soc_max = preferred_soc_max,
            soc_min_penalty = soc_min_penalty,
            soc_max_penalty = soc_max_penalty,
            terminal_slack = nothing,
        ),
    )
end

function component_tuple(components)
    return (
        components.model,
        components.u,
        components.y,
        components.Pg,
        components.mdot,
        components.lambda,
        components.P_ch,
        components.P_dis,
        components.E,
    )
end

function build_global_milp(
    gensets,
    load,
    battery,
    initial_commitment;
    terminal_energy_min_kwh=nothing,
)
    components = build_dispatch_model_core(gensets, load, battery, initial_commitment)

    if terminal_energy_min_kwh !== nothing
        @constraint(components.model, components.E[length(load) + 1] >= terminal_energy_min_kwh)
    end

    @objective(components.model, Min, components.fuel_startup_objective)

    return merge(
        components,
        (
            terminal_energy_min_kwh = terminal_energy_min_kwh,
            terminal_slack = nothing,
        ),
    )
end

function build_model(gensets, load, battery, initial_commitment)
    return component_tuple(
        build_global_milp(
            gensets,
            load,
            battery,
            initial_commitment;
            terminal_energy_min_kwh=battery.E_terminal_min,
        )
    )
end

function build_model_baseline(gensets, load, battery, initial_commitment)
    return component_tuple(
        build_global_milp(
            gensets,
            load,
            battery,
            initial_commitment;
            terminal_energy_min_kwh=nothing,
        )
    )
end

function build_rolling_horizon_milp(
    gensets,
    forecast_load,
    battery,
    previous_commitment,
    terminal_soft_target_kwh,
    terminal_slack_penalty,
)
    components = build_dispatch_model_core(gensets, forecast_load, battery, previous_commitment)
    H = length(forecast_load)

    @variable(components.model, s_term >= 0)
    @constraint(components.model, components.E[H + 1] + s_term >= terminal_soft_target_kwh)
    @objective(
        components.model,
        Min,
        components.fuel_startup_objective + terminal_slack_penalty * s_term
    )

    return merge(
        components,
        (
            terminal_slack = s_term,
            terminal_soft_target_kwh = terminal_soft_target_kwh,
            terminal_slack_penalty = terminal_slack_penalty,
        ),
    )
end
