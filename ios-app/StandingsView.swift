import SwiftUI

struct StandingsView: View {
    @StateObject private var apiService = APIService()
    @State private var league: League?
    @State private var isLoading = false
    @State private var errorMessage: String?
    
    let leagueId = "sample-league-1"
    
    var body: some View {
        NavigationView {
            Group {
                if isLoading {
                    loadingView
                } else if let league = league {
                    standingsContent(for: league)
                } else {
                    errorView
                }
            }
            .navigationTitle("College Football Pick6")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: refreshStandings) {
                        Image(systemName: "arrow.clockwise")
                            .foregroundColor(.primary)
                    }
                    .disabled(isLoading)
                }
            }
        }
        .task {
            await loadStandings()
        }
    }
    
    // MARK: - Views
    
    private var loadingView: some View {
        VStack(spacing: 20) {
            ProgressView()
                .scaleEffect(1.2)
            Text("Loading standings...")
                .font(.headline)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
    
    private var errorView: some View {
        VStack(spacing: 20) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 50))
                .foregroundColor(.orange)
            
            Text("Unable to load standings")
                .font(.headline)
            
            if let errorMessage = errorMessage {
                Text(errorMessage)
                    .font(.body)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }
            
            Button("Try Again") {
                Task { await loadStandings() }
            }
            .buttonStyle(.borderedProminent)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
    }
    
    private func standingsContent(for league: League) -> some View {
        ScrollView {
            LazyVStack(spacing: 0) {
                // League Header
                leagueHeaderView(league: league)
                
                // Standings List
                ForEach(Array(league.sortedMembers.enumerated()), id: \.element.id) { index, member in
                    StandingRowView(
                        member: member,
                        position: index + 1,
                        isCurrentUser: member.displayName == "Mike" // Stub current user
                    )
                    .padding(.horizontal)
                    .padding(.vertical, 8)
                }
            }
        }
        .refreshable {
            await loadStandings()
        }
    }
    
    private func leagueHeaderView(league: League) -> some View {
        VStack(spacing: 12) {
            Text(league.name)
                .font(.title2)
                .fontWeight(.bold)
                .multilineTextAlignment(.center)
            
            Text("Season \(league.season)")
                .font(.subheadline)
                .foregroundColor(.secondary)
            
            statusBadge(for: league.status)
        }
        .padding()
        .background(Color(UIColor.systemGroupedBackground))
    }
    
    private func statusBadge(for status: LeagueStatus) -> some View {
        Text(status.rawValue.capitalized)
            .font(.caption)
            .fontWeight(.medium)
            .padding(.horizontal, 12)
            .padding(.vertical, 4)
            .background(statusColor(for: status))
            .foregroundColor(.white)
            .clipShape(Capsule())
    }
    
    private func statusColor(for status: LeagueStatus) -> Color {
        switch status {
        case .draft:
            return .orange
        case .active:
            return .green
        case .completed:
            return .blue
        }
    }
    
    // MARK: - Actions
    
    private func loadStandings() async {
        isLoading = true
        errorMessage = nil
        
        do {
            let fetchedLeague = try await apiService.fetchLeagueStandings(leagueId: leagueId)
            league = fetchedLeague
        } catch {
            errorMessage = error.localizedDescription
        }
        
        isLoading = false
    }
    
    private func refreshStandings() {
        Task {
            await loadStandings()
        }
    }
}

// MARK: - Standing Row View

struct StandingRowView: View {
    let member: LeagueMember
    let position: Int
    let isCurrentUser: Bool
    
    var body: some View {
        HStack(spacing: 16) {
            // Position
            positionView
            
            // Member info
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(member.displayName)
                        .font(.headline)
                        .fontWeight(isCurrentUser ? .bold : .medium)
                    
                    if isCurrentUser {
                        Text("(You)")
                            .font(.caption)
                            .foregroundColor(.blue)
                    }
                }
                
                Text("\(member.teams.count) teams")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
            
            // Wins
            VStack(alignment: .trailing, spacing: 2) {
                Text("\(member.wins)")
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundColor(.primary)
                
                Text("wins")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(isCurrentUser ? Color.blue.opacity(0.1) : Color(UIColor.secondarySystemGroupedBackground))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(isCurrentUser ? Color.blue.opacity(0.3) : Color.clear, lineWidth: 1)
        )
    }
    
    private var positionView: some View {
        ZStack {
            Circle()
                .fill(positionColor)
                .frame(width: 32, height: 32)
            
            Text("\(position)")
                .font(.caption)
                .fontWeight(.bold)
                .foregroundColor(.white)
        }
    }
    
    private var positionColor: Color {
        switch position {
        case 1:
            return .yellow
        case 2:
            return .gray
        case 3:
            return Color(red: 0.8, green: 0.5, blue: 0.2) // Bronze
        default:
            return .secondary
        }
    }
}

// MARK: - Preview

#Preview {
    StandingsView()
} 