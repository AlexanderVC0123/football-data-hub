CREATE TABLE IF NOT EXISTS competitions (
    id SERIAL PRIMARY KEY,
    api_id INT UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20),
    country_name VARCHAR(50),
    type VARCHAR(50),
    emblem_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    api_id INT UNIQUE NOT NULL, 
    name VARCHAR(100) NOT NULL,
    short_name VARCHAR(50),
    tla VARCHAR(10),
    founded INT,
    venue VARCHAR(100),
    website TEXT,
    club_colors VARCHAR(100),
    address TEXT,
    crest_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS seasons(
    id SERIAL PRIMARY KEY,
    api_id INT UNIQUE,
    competition_id INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    current_matchday INT,
    winner_team_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_season_competition FOREIGN KEY (competition_id) REFERENCES competitions(id) ON DELETE CASCADE,
    CONSTRAINT fk_season_winner FOREIGN KEY (winner_team_id) REFERENCES teams(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY, 
    api_id INT UNIQUE NOT NULL,
    competition_id INT NOT NULL,
    season_id INT NOT NULL,
    matchday INT,
    utc_date TIMESTAMP NOT NULL,
    status VARCHAR(30),
    home_team_id INT NOT NULL,
    away_team_id INT NOT NULL,
    home_score INT,
    away_score INT,
    winner VARCHAR(10),
    stage VARCHAR(50),
    group_name VARCHAR(50),
    last_updated TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_match_competition FOREIGN KEY (competition_id) REFERENCES competitions(id) ON DELETE CASCADE,
    CONSTRAINT fk_match_season FOREIGN KEY (season_id) REFERENCES seasons(id) ON DELETE CASCADE,
    CONSTRAINT fk_match_home_team FOREIGN KEY (home_team_id) REFERENCES teams(id) ON DELETE CASCADE,
    CONSTRAINT fk_match_away_team FOREIGN KEY (away_team_id) REFERENCES teams(id) ON DELETE CASCADE,
    CONSTRAINT chk_different_teams CHECK (home_team_id <> away_team_id)
);

CREATE TABLE IF NOT EXISTS standings (
    id SERIAL PRIMARY KEY,
    competition_id INT NOT NULL,
    season_id INT NOT NULL,
    team_id INT NOT NULL,
    position INT NOT NULL,
    played_games INT DEFAULT 0,
    won INT DEFAULT 0,
    draw INT DEFAULT 0,
    lost INT DEFAULT 0,
    points INT DEFAULT 0,
    goals_for INT DEFAULT 0,
    goals_against INT DEFAULT 0,
    goal_difference INT DEFAULT 0,
    form VARCHAR(50),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_standing_competition FOREIGN KEY (competition_id) REFERENCES competitions(id) ON DELETE CASCADE,
    CONSTRAINT fk_standing_season FOREIGN KEY (season_id) REFERENCES seasons(id) ON DELETE CASCADE,
    CONSTRAINT fk_standing_team FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    CONSTRAINT uq_standing_unique_team_season UNIQUE (season_id, team_id)
);