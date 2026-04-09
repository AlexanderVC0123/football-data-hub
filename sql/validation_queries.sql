-- Ver cuántos registros hay en cada tabla
SELECT COUNT(*) AS total_competitions FROM competitions;
SELECT COUNT(*) AS total_teams FROM teams;
SELECT COUNT(*) AS total_seasons FROM seasons;
SELECT COUNT(*) AS total_standings FROM standings;
SELECT COUNT(*) AS total_matches FROM matches;

--Comprobar que la clasificación está bien insertada
SELECT
    s.position,
    t.name AS team,
    s.played_games,
    s.won,
    s.draw,
    s.lost,
    s.points,
    s.goals_for,
    s.goals_against,
    s.goal_difference
FROM standings s
JOIN teams t ON s.team_id = t.id
ORDER BY s.position;

--Comprobar que los partidos están bien insertados
SELECT
    m.matchday,
    m.utc_date,
    ht.name AS home_team,
    at.name AS away_team,
    m.home_score,
    m.away_score,
    m.status
FROM matches m
JOIN teams ht ON m.home_team_id = ht.id
JOIN teams at ON m.away_team_id = at.id
ORDER BY m.utc_date
LIMIT 20;

--Ver si hay partidos con fechas nulas. Debe dar 0
SELECT COUNT(*) AS matches_without_date
FROM matches
WHERE utc_date IS NULL;

--Ver si hay partidos con el mismo equipo como local y visitante. Debe dar 0
SELECT COUNT(*) AS invalid_matches
FROM matches
WHERE home_team_id = away_team_id;

--Ver si hay standings sin equipo asociado. Debe dar 0
SELECT COUNT(*) AS standings_without_team
FROM standings
WHERE team_id IS NULL;

--Ver la temporada insertada
SELECT *
FROM seasons;


--Ver la competición relacionada con la temporada
SELECT
    s.id AS season_id,
    s.api_id AS season_api_id,
    c.name AS competition_name,
    c.code
FROM seasons s
JOIN competitions c ON s.competition_id = c.id;

--Consulta de validación potente
SELECT
    c.name AS competition,
    t.name AS team,
    s.position,
    s.points
FROM standings s
JOIN teams t ON s.team_id = t.id
JOIN competitions c ON s.competition_id = c.id
ORDER BY s.position;
