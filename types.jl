"""This is not currently in use, but it is a good idea to separate the types from the main code for better organization and readability.

struct GeneratorParams
    P_max::Float64
    P_min::Float64

    SFOCbp::Vector{Float64}
    P::Vector{Float64}
end

struct BatteryParams
    P_ch_max::Float64
    P_dis_max::Float64
    E_max::Float64
    E_min::Float64
end

"""

#To be fetched in main:
    #P_max = 385.0
    #P_min = 0.5 * 385.0
    #Fbp = [193,191,191,198] #g/kWh [50%, 75%,80% ish, 100%]load
    #P = [0.5*385, 0.75*385, 310, 385] #Percentage power load levels
    #N = 1:2
    #I = 1:4