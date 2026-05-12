package repository

import (
	"context"
	"database/sql"
	"regexp"
	"strings"

	"info-serve/internal/events"
)

func (s *MySQLStore) ListEvents(ctx context.Context, params events.ListEventsParams) (events.EventPage, error) {
	whereSQL, args := buildEventWhere(params)
	countSQL := `SELECT COUNT(e.id) FROM event AS e JOIN category AS c ON c.id = e.primary_category_id ` + whereSQL

	var total int
	if err := s.db.QueryRowContext(ctx, countSQL, args...).Scan(&total); err != nil {
		return events.EventPage{}, err
	}

	orderSQL := "ORDER BY e.composite_score DESC, e.last_updated_at DESC"
	if params.Sort == "latest" {
		orderSQL = "ORDER BY e.last_updated_at DESC, e.composite_score DESC"
	}
	offset := (params.Page - 1) * params.PageSize
	listArgs := append(args, params.PageSize, offset)
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT e.id, e.title, e.one_line_summary, c.code, c.name,
		       e.heat_score, e.freshness_score, e.composite_score,
		       COALESCE(DATE_FORMAT(e.last_updated_at, '%Y-%m-%d %H:%i:%s'), ''),
		       e.source_count, e.previous_event_id, COALESCE(e.event_generation, 1), COALESCE(e.evolution_stage, 'emerging')
FROM event AS e
JOIN category AS c ON c.id = e.primary_category_id `+whereSQL+` `+orderSQL+` LIMIT ? OFFSET ?`,
		listArgs...,
	)
	if err != nil {
		return events.EventPage{}, err
	}
	defer rows.Close()

	items := []events.EventListItem{}
	for rows.Next() {
		var item events.EventListItem
		if err := rows.Scan(
			&item.ID,
			&item.Title,
			&item.OneLineSummary,
			&item.PrimaryCategory.Code,
			&item.PrimaryCategory.Name,
			&item.HeatScore,
			&item.FreshnessScore,
			&item.CompositeScore,
			&item.LastUpdatedAt,
			&item.SourceCount,
			&item.PreviousEventID,
			&item.EventGeneration,
			&item.EvolutionStage,
		); err != nil {
			return events.EventPage{}, err
		}
		representativeInfoID, err := s.representativeInfoID(ctx, item.ID)
		if err != nil {
			return events.EventPage{}, err
		}
		item.RepresentativeInfoID = representativeInfoID
		sourceBadges, err := s.sourceBadges(ctx, item.ID)
		if err != nil {
			return events.EventPage{}, err
		}
		item.SourceBadges = sourceBadges
		if item.SourceCount > 1 {
			item.NewUpdateCount = item.SourceCount - 1
		}
		items = append(items, item)
	}
	if err := rows.Err(); err != nil {
		return events.EventPage{}, err
	}
	return events.EventPage{Total: total, Page: params.Page, PageSize: params.PageSize, Items: items}, nil
}

func (s *MySQLStore) GetEventDetail(ctx context.Context, id int64) (events.EventDetail, error) {
	var event events.EventCore
	err := s.db.QueryRowContext(
		ctx,
		`SELECT e.id, e.title, e.one_line_summary, c.code, c.name,
		       e.heat_score, e.freshness_score, e.composite_score, e.source_count,
		       COALESCE(DATE_FORMAT(e.last_updated_at, '%Y-%m-%d %H:%i:%s'), ''),
		       e.previous_event_id, COALESCE(e.event_generation, 1), COALESCE(e.evolution_stage, 'emerging')
FROM event AS e
JOIN category AS c ON c.id = e.primary_category_id
WHERE e.id = ?`,
		id,
	).Scan(
		&event.ID,
		&event.Title,
		&event.OneLineSummary,
		&event.PrimaryCategory.Code,
		&event.PrimaryCategory.Name,
		&event.HeatScore,
		&event.FreshnessScore,
		&event.CompositeScore,
		&event.SourceCount,
		&event.LastUpdatedAt,
		&event.PreviousEventID,
		&event.EventGeneration,
		&event.EvolutionStage,
	)
	if err != nil {
		return events.EventDetail{}, err
	}

	timeline, err := s.eventTimeline(ctx, id)
	if err != nil {
		return events.EventDetail{}, err
	}
	summaries, err := s.eventSummaries(ctx, id)
	if err != nil {
		return events.EventDetail{}, err
	}
	sourceViews, err := s.eventSourceViews(ctx, id, summaries)
	if err != nil {
		return events.EventDetail{}, err
	}
	representativeSources, err := s.representativeSources(ctx, id)
	if err != nil {
		return events.EventDetail{}, err
	}
	techContext, err := s.eventTechContext(ctx, id)
	if err != nil {
		return events.EventDetail{}, err
	}

	return events.EventDetail{
		Event:                 event,
		Timeline:              timeline,
		Summaries:             summaries,
		SourceViews:           sourceViews,
		RepresentativeSources: representativeSources,
		TechContext:           techContext,
	}, nil
}

func buildEventWhere(params events.ListEventsParams) (string, []any) {
	clauses := []string{"e.status = 'active'"}
	args := []any{}
	if params.CategoryCode != "" && params.CategoryCode != "all" {
		clauses = append(clauses, "c.code = ?")
		args = append(args, params.CategoryCode)
	}
	if strings.TrimSpace(params.ChannelCode) != "" && strings.TrimSpace(params.ChannelCode) != "all" {
		clauses = append(
			clauses,
			`EXISTS (
				SELECT 1
				FROM event_item_link AS filter_link
				JOIN info AS filter_info ON filter_info.id = filter_link.item_id
				JOIN channel AS filter_channel ON filter_channel.id = filter_info.channel_id
				WHERE filter_link.event_id = e.id AND filter_channel.code = ?
			)`,
		)
		args = append(args, strings.TrimSpace(params.ChannelCode))
	}
	if strings.TrimSpace(params.Keyword) != "" {
		keyword := "%" + strings.TrimSpace(params.Keyword) + "%"
		clauses = append(clauses, "(e.title LIKE ? OR e.one_line_summary LIKE ?)")
		args = append(args, keyword, keyword)
	}
	return "WHERE " + strings.Join(clauses, " AND "), args
}

func (s *MySQLStore) representativeInfoID(ctx context.Context, eventID int64) (*int64, error) {
	var id int64
	err := s.db.QueryRowContext(
		ctx,
		`SELECT item_id FROM event_item_link WHERE event_id = ? ORDER BY is_primary DESC, weight DESC, id ASC LIMIT 1`,
		eventID,
	).Scan(&id)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &id, nil
}

func (s *MySQLStore) sourceBadges(ctx context.Context, eventID int64) ([]string, error) {
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT ch.name
FROM event_item_link AS link
JOIN info AS i ON i.id = link.item_id
JOIN channel AS ch ON ch.id = i.channel_id
WHERE link.event_id = ?
GROUP BY ch.name
ORDER BY MAX(link.weight) DESC
LIMIT 3`,
		eventID,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	badges := []string{}
	for rows.Next() {
		var name string
		if err := rows.Scan(&name); err != nil {
			return nil, err
		}
		badges = append(badges, name)
	}
	return badges, rows.Err()
}

func (s *MySQLStore) eventTimeline(ctx context.Context, eventID int64) ([]events.TimelineItem, error) {
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT id, DATE_FORMAT(occurred_at, '%Y-%m-%d %H:%i:%s'), summary, confidence
FROM event_timeline_entry
WHERE event_id = ?
ORDER BY occurred_at ASC`,
		eventID,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := []events.TimelineItem{}
	for rows.Next() {
		var item events.TimelineItem
		if err := rows.Scan(&item.ID, &item.OccurredAt, &item.Summary, &item.Confidence); err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, rows.Err()
}

func (s *MySQLStore) eventSummaries(ctx context.Context, eventID int64) (map[string]string, error) {
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT summary_type, content FROM event_summary_snapshot WHERE event_id = ? ORDER BY version DESC, id DESC`,
		eventID,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	result := map[string]string{}
	for rows.Next() {
		var summaryType string
		var content sql.NullString
		if err := rows.Scan(&summaryType, &content); err != nil {
			return nil, err
		}
		if _, exists := result[summaryType]; !exists && content.Valid {
			result[summaryType] = content.String
		}
	}
	return result, rows.Err()
}

func (s *MySQLStore) eventSourceViews(ctx context.Context, eventID int64, summaries map[string]string) ([]events.SourceView, error) {
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT ch.name, COALESCE(i.content, '')
FROM event_item_link AS link
JOIN info AS i ON i.id = link.item_id
JOIN channel AS ch ON ch.id = i.channel_id
WHERE link.event_id = ?
ORDER BY link.weight DESC
LIMIT 6`,
		eventID,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	result := []events.SourceView{}
	seen := map[string]bool{}
	for rows.Next() {
		var channelName string
		var content string
		if err := rows.Scan(&channelName, &content); err != nil {
			return nil, err
		}
		if seen[channelName] {
			continue
		}
		summary := compactInlineText(content, 240)
		if summary == "" || redundantWithSummaries(summary, summaries) {
			continue
		}
		result = append(result, events.SourceView{ChannelName: channelName, Summary: summary})
		seen[channelName] = true
		if len(result) >= 3 {
			break
		}
	}
	return result, rows.Err()
}

func (s *MySQLStore) representativeSources(ctx context.Context, eventID int64) ([]events.RepresentativeSource, error) {
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT i.id, i.title, ch.name, i.source_url, COALESCE(DATE_FORMAT(i.event_time, '%Y-%m-%d %H:%i:%s'), ''),
		       COALESCE(i.content, ''), COALESCE(i.detail_fetch_status, ''), i.detail_score, i.detail_content_length
FROM event_item_link AS link
JOIN info AS i ON i.id = link.item_id
JOIN channel AS ch ON ch.id = i.channel_id
WHERE link.event_id = ?
ORDER BY
  CASE WHEN i.detail_fetch_status = 'complete' THEN 0 WHEN i.detail_fetch_status = 'partial' THEN 1 ELSE 2 END ASC,
  i.detail_score DESC,
  i.detail_content_length DESC,
  link.weight DESC
LIMIT 6`,
		eventID,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	result := []events.RepresentativeSource{}
	for rows.Next() {
		var item events.RepresentativeSource
		var content string
		if err := rows.Scan(
			&item.InfoID,
			&item.Title,
			&item.ChannelName,
			&item.SourceURL,
			&item.EventTime,
			&content,
			&item.DetailFetchStatus,
			&item.DetailScore,
			&item.DetailContentLength,
		); err != nil {
			return nil, err
		}
		item.Content = compactArticleText(content, 6000)
		result = append(result, item)
	}
	return result, rows.Err()
}

func (s *MySQLStore) eventTechContext(ctx context.Context, eventID int64) (events.TechContext, error) {
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT tech_topic_type, tech_entities, tech_keywords
FROM event_item_link AS link
JOIN info AS i ON i.id = link.item_id
WHERE link.event_id = ?`,
		eventID,
	)
	if err != nil {
		return events.TechContext{}, err
	}
	defer rows.Close()
	topicCounts := map[string]int{}
	entityCounts := map[string]int{}
	keywordCounts := map[string]int{}
	for rows.Next() {
		var topic string
		var entities string
		var keywords string
		if err := rows.Scan(&topic, &entities, &keywords); err != nil {
			return events.TechContext{}, err
		}
		if strings.TrimSpace(topic) != "" {
			topicCounts[topic]++
		}
		addCSVCounts(entityCounts, entities)
		addCSVCounts(keywordCounts, keywords)
	}
	return events.TechContext{
		Topics:   topTopics(topicCounts, 3),
		Entities: topKeys(entityCounts, 6),
		Keywords: topKeys(keywordCounts, 8),
	}, rows.Err()
}

func addCSVCounts(target map[string]int, raw string) {
	for _, part := range strings.Split(raw, ",") {
		value := strings.TrimSpace(part)
		if value != "" {
			target[value]++
		}
	}
}

func topTopics(counts map[string]int, limit int) []events.TechTopic {
	keys := topKeys(counts, limit)
	result := make([]events.TechTopic, 0, len(keys))
	for _, key := range keys {
		result = append(result, events.TechTopic{TopicType: key, Count: counts[key]})
	}
	return result
}

func topKeys(counts map[string]int, limit int) []string {
	result := []string{}
	for len(result) < limit {
		bestKey := ""
		bestCount := 0
		for key, count := range counts {
			if containsString(result, key) {
				continue
			}
			if count > bestCount || (count == bestCount && (bestKey == "" || key < bestKey)) {
				bestKey = key
				bestCount = count
			}
		}
		if bestKey == "" {
			break
		}
		result = append(result, bestKey)
	}
	return result
}

func containsString(values []string, target string) bool {
	for _, value := range values {
		if value == target {
			return true
		}
	}
	return false
}

func compactInlineText(value string, maxRuneCount int) string {
	cleaned := strings.Join(strings.Fields(value), " ")
	runes := []rune(cleaned)
	if len(runes) <= maxRuneCount {
		return cleaned
	}
	return strings.TrimSpace(string(runes[:maxRuneCount])) + "..."
}

func compactArticleText(value string, maxRuneCount int) string {
	cleaned := normalizeArticleText(value)
	runes := []rune(cleaned)
	if len(runes) <= maxRuneCount {
		return cleaned
	}
	return strings.TrimSpace(string(runes[:maxRuneCount])) + "..."
}

func normalizeArticleText(value string) string {
	text := strings.ReplaceAll(value, "\r\n", "\n")
	text = strings.ReplaceAll(text, "\r", "\n")
	lines := []string{}
	for _, line := range strings.Split(text, "\n") {
		cleaned := strings.Join(strings.Fields(line), " ")
		if cleaned != "" {
			lines = append(lines, cleaned)
		}
	}
	if len(lines) > 1 {
		return strings.Join(lines, "\n\n")
	}
	cleaned := strings.Join(strings.Fields(value), " ")
	cleaned = regexp.MustCompile(`\s+([，。！？；：、,.!?;:])`).ReplaceAllString(cleaned, "$1")
	cleaned = regexp.MustCompile(`([。！？!?])\s+`).ReplaceAllString(cleaned, "$1\n\n")
	cleaned = regexp.MustCompile(`\n{3,}`).ReplaceAllString(cleaned, "\n\n")
	return strings.TrimSpace(cleaned)
}

func redundantWithSummaries(value string, summaries map[string]string) bool {
	if value == "" {
		return true
	}
	for _, summary := range summaries {
		if summary == "" {
			continue
		}
		if strings.Contains(summary, value) || strings.Contains(value, summary) {
			return true
		}
	}
	return false
}
