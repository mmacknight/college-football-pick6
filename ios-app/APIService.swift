import Foundation

// MARK: - API Service (Stub Implementation)

@MainActor
class APIService: ObservableObject {
    
    // MARK: - Stub Functions
    
    /// Fetches league standings with simulated network delay
    func fetchLeagueStandings(leagueId: String) async throws -> League {
        // Simulate network delay
        try await Task.sleep(nanoseconds: 500_000_000) // 0.5 seconds
        
        // Return hardcoded data
        return League.sampleLeague
    }
    
    /// Updates win count for a team (stub)
    func updateTeamWins(leagueId: String, teamId: String, wins: Int) async throws {
        try await Task.sleep(nanoseconds: 300_000_000) // 0.3 seconds
        print("📊 Stub: Updated \(teamId) to \(wins) wins in league \(leagueId)")
    }
    
    /// Fetches all available teams
    func fetchAvailableTeams() async throws -> [Team] {
        try await Task.sleep(nanoseconds: 400_000_000) // 0.4 seconds
        return Team.sampleTeams
    }
    
    /// Creates a new league (stub)
    func createLeague(name: String, season: String) async throws -> League {
        try await Task.sleep(nanoseconds: 600_000_000) // 0.6 seconds
        
        return League(
            id: UUID().uuidString,
            name: name,
            season: season,
            members: [],
            status: .draft
        )
    }
    
    /// Joins a league by code (stub)
    func joinLeague(joinCode: String) async throws -> League {
        try await Task.sleep(nanoseconds: 500_000_000) // 0.5 seconds
        return League.sampleLeague
    }
    
    /// Makes a draft pick (stub)
    func makeDraftPick(leagueId: String, teamId: String) async throws {
        try await Task.sleep(nanoseconds: 400_000_000) // 0.4 seconds
        print("🏈 Stub: Picked team \(teamId) in league \(leagueId)")
    }
    
    /// Fetches user's leagues (stub)
    func fetchUserLeagues() async throws -> [League] {
        try await Task.sleep(nanoseconds: 600_000_000) // 0.6 seconds
        return [League.sampleLeague]
    }
    
    /// Refreshes scores from external API (stub)
    func refreshScores(leagueId: String) async throws {
        try await Task.sleep(nanoseconds: 1_000_000_000) // 1 second
        print("🔄 Stub: Refreshed scores for league \(leagueId)")
    }
}

// MARK: - Error Types

enum APIError: Error, LocalizedError {
    case networkError
    case invalidResponse
    case unauthorized
    case notFound
    
    var errorDescription: String? {
        switch self {
        case .networkError:
            return "Network connection failed"
        case .invalidResponse:
            return "Invalid server response"
        case .unauthorized:
            return "Authentication required"
        case .notFound:
            return "Resource not found"
        }
    }
} 