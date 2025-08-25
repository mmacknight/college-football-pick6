import Foundation

// MARK: - Data Models

struct Team: Identifiable, Codable {
    let id: String
    let name: String
    let mascot: String
    let conference: String
    let primaryColor: String
    let logoUrl: String?
    
    var displayName: String {
        "\(name) \(mascot)"
    }
}

struct LeagueMember: Identifiable, Codable {
    let id: String
    let displayName: String
    let teams: [Team]
    let wins: Int
    
    var winPercentage: Double {
        guard !teams.isEmpty else { return 0.0 }
        return Double(wins) / Double(teams.count * 12) // Assuming ~12 games per team
    }
}

struct League: Identifiable, Codable {
    let id: String
    let name: String
    let season: String
    let members: [LeagueMember]
    let status: LeagueStatus
    
    var sortedMembers: [LeagueMember] {
        members.sorted { $0.wins > $1.wins }
    }
}

enum LeagueStatus: String, Codable, CaseIterable {
    case draft = "draft"
    case active = "active"
    case completed = "completed"
}

// MARK: - Hardcoded Data

extension Team {
    static let sampleTeams: [Team] = [
        Team(id: "alabama", name: "Alabama", mascot: "Crimson Tide", conference: "SEC", primaryColor: "#9E1B32", logoUrl: nil),
        Team(id: "georgia", name: "Georgia", mascot: "Bulldogs", conference: "SEC", primaryColor: "#BA0C2F", logoUrl: nil),
        Team(id: "michigan", name: "Michigan", mascot: "Wolverines", conference: "Big Ten", primaryColor: "#00274C", logoUrl: nil),
        Team(id: "texas", name: "Texas", mascot: "Longhorns", conference: "Big 12", primaryColor: "#BF5700", logoUrl: nil),
        Team(id: "ohiostate", name: "Ohio State", mascot: "Buckeyes", conference: "Big Ten", primaryColor: "#BB0000", logoUrl: nil),
        Team(id: "oregon", name: "Oregon", mascot: "Ducks", conference: "Pac-12", primaryColor: "#18453B", logoUrl: nil),
        Team(id: "clemson", name: "Clemson", mascot: "Tigers", conference: "ACC", primaryColor: "#F66733", logoUrl: nil),
        Team(id: "usc", name: "USC", mascot: "Trojans", conference: "Pac-12", primaryColor: "#990000", logoUrl: nil),
        Team(id: "miami", name: "Miami", mascot: "Hurricanes", conference: "ACC", primaryColor: "#F47321", logoUrl: nil),
        Team(id: "florida", name: "Florida", mascot: "Gators", conference: "SEC", primaryColor: "#0021A5", logoUrl: nil),
        Team(id: "lsu", name: "LSU", mascot: "Tigers", conference: "SEC", primaryColor: "#461D7C", logoUrl: nil),
        Team(id: "notredame", name: "Notre Dame", mascot: "Fighting Irish", conference: "Independent", primaryColor: "#0C2340", logoUrl: nil),
        Team(id: "oklahoma", name: "Oklahoma", mascot: "Sooners", conference: "Big 12", primaryColor: "#841617", logoUrl: nil),
        Team(id: "wisconsin", name: "Wisconsin", mascot: "Badgers", conference: "Big Ten", primaryColor: "#C5050C", logoUrl: nil),
        Team(id: "pennstate", name: "Penn State", mascot: "Nittany Lions", conference: "Big Ten", primaryColor: "#041E42", logoUrl: nil),
        Team(id: "tennessee", name: "Tennessee", mascot: "Volunteers", conference: "SEC", primaryColor: "#FF8200", logoUrl: nil)
    ]
}

extension League {
    static let sampleLeague = League(
        id: "sample-league-1",
        name: "Championship Chase 2024",
        season: "2024",
        members: [
            LeagueMember(
                id: "user1",
                displayName: "Mike",
                teams: [
                    Team.sampleTeams[0], // Alabama
                    Team.sampleTeams[2], // Michigan
                    Team.sampleTeams[6], // Clemson
                    Team.sampleTeams[11] // Notre Dame
                ],
                wins: 42
            ),
            LeagueMember(
                id: "user2",
                displayName: "Sarah",
                teams: [
                    Team.sampleTeams[1], // Georgia
                    Team.sampleTeams[4], // Ohio State
                    Team.sampleTeams[9], // Florida
                    Team.sampleTeams[14] // Penn State
                ],
                wins: 38
            ),
            LeagueMember(
                id: "user3",
                displayName: "Alex",
                teams: [
                    Team.sampleTeams[3], // Texas
                    Team.sampleTeams[5], // Oregon
                    Team.sampleTeams[7], // USC
                    Team.sampleTeams[12] // Oklahoma
                ],
                wins: 35
            ),
            LeagueMember(
                id: "user4",
                displayName: "Jordan",
                teams: [
                    Team.sampleTeams[8], // Miami
                    Team.sampleTeams[10], // LSU
                    Team.sampleTeams[13], // Wisconsin
                    Team.sampleTeams[15] // Tennessee
                ],
                wins: 31
            )
        ],
        status: .active
    )
} 