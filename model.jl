
function build_model(gensets, load)
    model = Model(HiGHS.Optimizer)

    G = 1:length(gensets)
    T = 1:length(load)

    #Decision variables
    @variable(model, u[g in G, t in T], Bin) #Generator on/off status
    @variable(model, Pg[g in G, t in T] >= 0) #Generator power output
    @variable(model, Fg[g in G, t in T] >= 0) #Fuel flow
    @variable(model, 0 <= lambda[g in G, t in T, i in 1:length(gensets[g].Fbp)] <= 1) #convex-combination weights

    for t in T
        # Power balance constraint
        @constraint(model, sum(Pg[g, t] for g in G) == load[t])

        for g in G
            #Constraints
            @constraint(model, Pg[g, t] >= gensets[g].P_min * u[g, t])
            @constraint(model, Pg[g, t] <= gensets[g].P_max * u[g, t])

            # If generator is on, weights must sum to 1. If off, weights must sum to 0.
            @constraint(model, sum(lambda[g, t, i] for i in 1:length(gensets[g].Fbp)) == u[g, t])

            # Generator power as convex combination of breakpoint powers
            @constraint(model, Pg[g, t] == sum(lambda[g, t, i] * gensets[g].P[i] for i in 1:length(gensets[g].Fbp)))

            # Fuel flow as convex combination of breakpoint fuel flows
            @constraint(model, Fg[g, t] == sum(lambda[g, t, i] * gensets[g].Fbp[i] for i in 1:length(gensets[g].Fbp)))

            #SOS2 constraints
            @constraint(model, [lambda[g, t, i] for i in 1:length(gensets[g].Fbp)] in SOS2())
        end

        # Symmetry-breaking: enforce ordering on identical generators per time step
        for g in 1:(length(G)-1)
            @constraint(model, Pg[g, t] >= Pg[g+1, t])
        end
    end

    #Objective: minimize total fuel flow over all time steps
    @objective(model, Min, sum(Fg[g, t] for g in G, t in T))

    return model, u, Pg, Fg, lambda
end


#Hmm må vurdere hvorvidt jeg trenger spenningsgrenser på DClink etc..7

