package events

import (
	"context"
	"strings"
)

// Store 定义事件读取所需的数据访问能力。
type Store interface {
	ListEvents(ctx context.Context, params ListEventsParams) (EventPage, error)
	GetEventDetail(ctx context.Context, id int64) (EventDetail, error)
}

// Service 封装用户侧事件读取规则。
type Service struct {
	store Store
}

type ListEventsParams struct {
	CategoryCode string
	ChannelCode  string
	Keyword      string
	Status       string
	Sort         string
	Page         int
	PageSize     int
}

type EventCategory struct {
	Code         string `json:"code"`
	Name         string `json:"name"`
	DisplayOrder int    `json:"display_order"`
}

type CategoryBrief struct {
	Code string `json:"code"`
	Name string `json:"name"`
}

type EventListItem struct {
	ID                   int64         `json:"id"`
	RepresentativeInfoID *int64        `json:"representative_info_id"`
	Status               string        `json:"status"`
	Title                string        `json:"title"`
	OneLineSummary       string        `json:"one_line_summary"`
	PrimaryCategory      CategoryBrief `json:"primary_category"`
	HeatScore            int           `json:"heat_score"`
	FreshnessScore       int           `json:"freshness_score"`
	CompositeScore       int           `json:"composite_score"`
	DisplayQualityScore  int           `json:"display_quality_score"`
	DisplayQualityLevel  string        `json:"display_quality_level"`
	DisplayQualityReason string        `json:"display_quality_reason"`
	LastUpdatedAt        string        `json:"last_updated_at"`
	SourceCount          int           `json:"source_count"`
	SourceBadges         []string      `json:"source_badges"`
	NewUpdateCount       int           `json:"new_update_count"`
	// 历史脉络字段
	PreviousEventID *int64 `json:"previous_event_id"`
	EventGeneration int    `json:"event_generation"`
	EvolutionStage  string `json:"evolution_stage"`
}

type EventPage struct {
	Total    int             `json:"total"`
	Page     int             `json:"page"`
	PageSize int             `json:"page_size"`
	Items    []EventListItem `json:"items"`
}

type EventCore struct {
	ID                   int64         `json:"id"`
	Status               string        `json:"status"`
	Title                string        `json:"title"`
	OneLineSummary       string        `json:"one_line_summary"`
	PrimaryCategory      CategoryBrief `json:"primary_category"`
	HeatScore            int           `json:"heat_score"`
	FreshnessScore       int           `json:"freshness_score"`
	CompositeScore       int           `json:"composite_score"`
	DisplayQualityScore  int           `json:"display_quality_score"`
	DisplayQualityLevel  string        `json:"display_quality_level"`
	DisplayQualityReason string        `json:"display_quality_reason"`
	SourceCount          int           `json:"source_count"`
	LastUpdatedAt        string        `json:"last_updated_at"`
	// 历史脉络字段
	PreviousEventID *int64 `json:"previous_event_id"`
	EventGeneration int    `json:"event_generation"`
	EvolutionStage  string `json:"evolution_stage"`
}

type TimelineItem struct {
	ID         int64   `json:"id"`
	OccurredAt string  `json:"occurred_at"`
	Summary    string  `json:"summary"`
	Confidence float64 `json:"confidence"`
}

type SourceView struct {
	ChannelName    string `json:"channel_name"`
	Summary        string `json:"summary"`
	Focus          string `json:"focus"`
	Stance         string `json:"stance"`
	DifferenceHint string `json:"difference_hint"`
}

type RepresentativeSource struct {
	InfoID              int64  `json:"info_id"`
	Title               string `json:"title"`
	ChannelName         string `json:"channel_name"`
	SourceURL           string `json:"source_url"`
	EventTime           string `json:"event_time"`
	Content             string `json:"content"`
	DetailFetchStatus   string `json:"detail_fetch_status"`
	DetailScore         int    `json:"detail_score"`
	DetailContentLength int    `json:"detail_content_length"`
}

type EvidenceSource struct {
	InfoID            int64    `json:"info_id"`
	Title             string   `json:"title"`
	ChannelName       string   `json:"channel_name"`
	SourceURL         string   `json:"source_url"`
	Weight            int      `json:"weight"`
	DetailScore       int      `json:"detail_score"`
	DetailFetchStatus string   `json:"detail_fetch_status"`
	QualityLevel      string   `json:"quality_level"`
	QualitySummary    string   `json:"quality_summary"`
	RiskReasons       []string `json:"risk_reasons"`
}

type PlatformView struct {
	ChannelName string `json:"channel_name"`
	SourceCount int    `json:"source_count"`
}

type EvidenceChain struct {
	EvidenceSources   []EvidenceSource `json:"evidence_sources"`
	WeakSources       []EvidenceSource `json:"weak_sources"`
	PlatformViews     []PlatformView   `json:"platform_views"`
	UsableSourceCount int              `json:"usable_source_count"`
	WeakSourceCount   int              `json:"weak_source_count"`
}

type TechTopic struct {
	TopicType string `json:"topic_type"`
	Count     int    `json:"count"`
}

type TechContext struct {
	Topics   []TechTopic `json:"topics"`
	Entities []string    `json:"entities"`
	Keywords []string    `json:"keywords"`
}

type IntelligenceBrief struct {
	Stage             string   `json:"stage"`
	ConfidenceReason  string   `json:"confidence_reason"`
	DecisionHint      string   `json:"decision_hint"`
	FollowUpQuestions []string `json:"follow_up_questions"`
}

type ControversyBrief struct {
	Level          string   `json:"level"`
	Title          string   `json:"title"`
	Summary        string   `json:"summary"`
	Signals        []string `json:"signals"`
	ActionHint     string   `json:"action_hint"`
	HasRumorSignal bool     `json:"has_rumor_signal"`
}

type RelatedEvent struct {
	ID               int64  `json:"id"`
	Title            string `json:"title"`
	OneLineSummary   string `json:"one_line_summary"`
	LastUpdatedAt    string `json:"last_updated_at"`
	RelationType     string `json:"relation_type"`
	RelationLabel    string `json:"relation_label"`
	RelationReason   string `json:"relation_reason"`
	EvolutionType    string `json:"evolution_type"`
	EvolutionSummary string `json:"evolution_summary"`
}

type EventDetail struct {
	Event                 EventCore              `json:"event"`
	Timeline              []TimelineItem         `json:"timeline"`
	Summaries             map[string]string      `json:"summaries"`
	SourceViews           []SourceView           `json:"source_views"`
	RepresentativeSources []RepresentativeSource `json:"representative_sources"`
	TechContext           TechContext            `json:"tech_context"`
	IntelligenceBrief     IntelligenceBrief      `json:"intelligence_brief"`
	EvidenceChain         EvidenceChain          `json:"evidence_chain"`
	ControversyBrief      ControversyBrief       `json:"controversy_brief"`
	RelatedEvents         []RelatedEvent         `json:"related_events"`
}

func NewService(store Store) *Service {
	return &Service{store: store}
}

func EventCategories() []EventCategory {
	return []EventCategory{
		{Code: "all", Name: "全网", DisplayOrder: 0},
		{Code: "tech", Name: "科技", DisplayOrder: 1},
		{Code: "economy", Name: "财经", DisplayOrder: 2},
		{Code: "sports", Name: "体育", DisplayOrder: 3},
		{Code: "international", Name: "国际", DisplayOrder: 4},
	}
}

func (s *Service) ListEvents(ctx context.Context, params ListEventsParams) (EventPage, error) {
	params.CategoryCode = strings.TrimSpace(params.CategoryCode)
	if params.CategoryCode == "" {
		params.CategoryCode = "all"
	}
	params.ChannelCode = strings.TrimSpace(params.ChannelCode)
	params.Status = strings.TrimSpace(params.Status)
	if params.Status != "monitoring" {
		params.Status = "active"
	}
	params.Sort = strings.TrimSpace(params.Sort)
	if params.Sort != "latest" {
		params.Sort = "composite"
	}
	if params.Page < 1 {
		params.Page = 1
	}
	if params.PageSize < 1 {
		params.PageSize = 10
	}
	if params.PageSize > 50 {
		params.PageSize = 50
	}
	page, err := s.store.ListEvents(ctx, params)
	if err != nil {
		return EventPage{}, err
	}
	for index := range page.Items {
		if page.Items[index].SourceBadges == nil {
			page.Items[index].SourceBadges = []string{}
		}
		page.Items[index].Title = displayTitle(page.Items[index].Title)
		page.Items[index].OneLineSummary = displayOneLineSummary(
			page.Items[index].Title,
			page.Items[index].OneLineSummary,
			page.Items[index].PrimaryCategory.Code,
			page.Items[index].SourceBadges,
		)
	}
	return page, nil
}

func (s *Service) GetEventDetail(ctx context.Context, id int64) (EventDetail, error) {
	detail, err := s.store.GetEventDetail(ctx, id)
	if err != nil {
		return EventDetail{}, err
	}
	detail.Event.Title = displayTitle(detail.Event.Title)
	detail.Event.OneLineSummary = displayOneLineSummary(
		detail.Event.Title,
		detail.Event.OneLineSummary,
		detail.Event.PrimaryCategory.Code,
		nil,
	)
	detail.SourceViews = enrichSourceViews(detail.SourceViews)
	detail.IntelligenceBrief = buildIntelligenceBrief(detail)
	detail.EvidenceChain = buildEvidenceChain(detail.RepresentativeSources)
	detail.ControversyBrief = buildControversyBrief(detail)
	detail.RelatedEvents = enrichRelatedEvents(detail.RelatedEvents)
	return detail, nil
}

func displayTitle(title string) string {
	cleanTitle := strings.Join(strings.Fields(strings.TrimSpace(title)), " ")
	if cleanTitle == "" {
		return cleanTitle
	}
	cleanTitle = strings.TrimSuffix(cleanTitle, "...")
	if !isLikelyTruncatedTitle(cleanTitle) {
		return cleanTitle
	}
	trimmed := trimTruncatedTitleTail(cleanTitle)
	if trimmed == "" {
		return cleanTitle + "..."
	}
	return strings.TrimSpace(trimmed) + "..."
}

func isLikelyTruncatedTitle(title string) bool {
	runes := []rune(title)
	if len(runes) < 38 || len(runes) > 90 {
		return false
	}
	last := runes[len(runes)-1]
	if strings.ContainsRune("。！？.!?」』）)]", last) {
		return false
	}
	if isMostlyASCII(title) {
		fields := strings.Fields(title)
		if len(fields) == 0 {
			return false
		}
		lastWord := strings.Trim(fields[len(fields)-1], ",;:-")
		if len([]rune(lastWord)) <= 4 || isEnglishTrailingStopWord(strings.ToLower(lastWord)) {
			return true
		}
		return len(runes) >= 40 && len([]rune(lastWord)) <= 6
	}
	return len(runes) >= 40
}

func trimTruncatedTitleTail(title string) string {
	if !isMostlyASCII(title) {
		runes := []rune(title)
		if len(runes) <= 4 {
			return title
		}
		return strings.TrimRight(string(runes[:len(runes)-1]), "，,、：:；;的了和与及在")
	}
	fields := strings.Fields(title)
	if len(fields) <= 1 {
		return title
	}
	for len(fields) > 1 {
		last := strings.Trim(fields[len(fields)-1], ",;:-")
		if len([]rune(last)) > 4 && !isEnglishTrailingStopWord(strings.ToLower(last)) {
			break
		}
		fields = fields[:len(fields)-1]
	}
	for len(fields) > 1 && isEnglishTrailingStopWord(strings.ToLower(strings.Trim(fields[len(fields)-1], ",;:-"))) {
		fields = fields[:len(fields)-1]
	}
	return strings.Join(fields, " ")
}

func isMostlyASCII(text string) bool {
	runes := []rune(text)
	if len(runes) == 0 {
		return true
	}
	ascii := 0
	for _, char := range runes {
		if char <= 127 {
			ascii++
		}
	}
	return float64(ascii)/float64(len(runes)) >= 0.8
}

func isEnglishTrailingStopWord(word string) bool {
	switch word {
	case "a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of", "on", "or", "the", "to", "with", "after", "before", "under", "over":
		return true
	default:
		return false
	}
}

func displayOneLineSummary(title string, summary string, categoryCode string, sourceBadges []string) string {
	cleanSummary := strings.TrimSpace(summary)
	if !isWeakDisplaySummary(cleanSummary, title) {
		return ensureSentence(cleanSummary)
	}
	cleanTitle := strings.TrimSpace(title)
	if cleanTitle == "" {
		return "该事件已有相关线索出现，仍需结合更多可靠来源持续跟进。"
	}
	prefix := "该事件"
	if categoryCode == "international" || hasSourceBadge(sourceBadges, "路透社") {
		prefix = "路透社披露"
	}
	return ensureSentence(prefix + "「" + truncateRunes(cleanTitle, 48) + "」，仍需结合后续可靠来源持续跟进")
}

func isWeakDisplaySummary(summary string, title string) bool {
	if summary == "" {
		return true
	}
	lower := strings.ToLower(summary)
	weakMarkers := []string{
		"reuters category:",
		"official reuters url:",
		"published at",
		"according to its official news sitemap",
		"相关讨论正在升温",
		"已出现多来源跟进",
	}
	for _, marker := range weakMarkers {
		if strings.Contains(lower, strings.ToLower(marker)) {
			return true
		}
	}
	if len([]rune(summary)) < 18 {
		return true
	}
	cleanTitle := strings.TrimSpace(title)
	return cleanTitle != "" && strings.HasPrefix(summary, truncateRunes(cleanTitle, 18))
}

func hasSourceBadge(sourceBadges []string, keyword string) bool {
	for _, badge := range sourceBadges {
		if strings.Contains(badge, keyword) {
			return true
		}
	}
	return false
}

func ensureSentence(text string) string {
	text = strings.TrimSpace(text)
	if text == "" {
		return text
	}
	if strings.HasSuffix(text, "。") || strings.HasSuffix(text, "！") || strings.HasSuffix(text, "？") {
		return text
	}
	return text + "。"
}

func truncateRunes(text string, limit int) string {
	runes := []rune(strings.TrimSpace(text))
	if limit <= 0 || len(runes) <= limit {
		return string(runes)
	}
	return string(runes[:limit])
}

func enrichRelatedEvents(items []RelatedEvent) []RelatedEvent {
	result := make([]RelatedEvent, 0, len(items))
	for _, item := range items {
		if strings.TrimSpace(item.RelationLabel) == "" {
			item.RelationLabel = relationLabel(item)
		}
		if strings.TrimSpace(item.RelationReason) == "" {
			item.RelationReason = relationReason(item)
		}
		result = append(result, item)
	}
	return result
}

func relationLabel(item RelatedEvent) string {
	switch item.RelationType {
	case "previous":
		return "前序事件"
	case "next":
		return "后续进展"
	default:
		return "相关事件"
	}
}

func relationReason(item RelatedEvent) string {
	if strings.TrimSpace(item.EvolutionSummary) != "" {
		return item.EvolutionSummary
	}
	switch item.EvolutionType {
	case "escalation":
		return "相比前序事件，热度或影响范围出现升级。"
	case "expansion":
		return "事件从原有线索扩展出新的来源或叙事角度。"
	case "correction":
		return "后续信息对前序事件进行了修正或澄清。"
	case "recurrence":
		return "同类事件再次出现，具备反复观察价值。"
	default:
		if item.RelationType == "previous" {
			return "这是当前事件的历史背景，可帮助判断它是否属于连续演变。"
		}
		if item.RelationType == "next" {
			return "这是当前事件之后的新进展，可继续跟踪事件走向。"
		}
		return "该事件与当前事件存在历史或主题关联。"
	}
}

func enrichSourceViews(sourceViews []SourceView) []SourceView {
	result := make([]SourceView, 0, len(sourceViews))
	for _, view := range sourceViews {
		text := view.ChannelName + " " + view.Summary
		if strings.TrimSpace(view.Focus) == "" {
			view.Focus = narrativeFocus(text)
		}
		if strings.TrimSpace(view.Stance) == "" {
			view.Stance = narrativeStance(text)
		}
		if strings.TrimSpace(view.DifferenceHint) == "" {
			view.DifferenceHint = narrativeDifferenceHint(view)
		}
		result = append(result, view)
	}
	return result
}

func narrativeFocus(text string) string {
	switch {
	case hasAny(text, "通报", "官方", "警方", "消防", "法院", "应急"):
		return "权威处置"
	case hasAny(text, "救援", "伤者", "治疗", "伤亡", "原因调查"):
		return "救援与后续"
	case hasAny(text, "质疑", "争议", "讨论", "网友", "微博", "评论"):
		return "公众讨论"
	case hasAny(text, "影响", "市场", "行业", "股价", "成本", "政策"):
		return "影响分析"
	case hasAny(text, "比赛", "赛程", "球队", "冠军", "退出"):
		return "赛程动态"
	case hasAny(text, "AI", "模型", "芯片", "开发者", "产品"):
		return "产业进展"
	default:
		return "事实补充"
	}
}

func narrativeStance(text string) string {
	switch {
	case hasAny(text, "通报", "官方", "确认", "宣布"):
		return "确认事实"
	case hasAny(text, "质疑", "争议", "传言", "网传", "假的", "辟谣"):
		return "等待核验"
	case hasAny(text, "分析", "影响", "意味着", "预计"):
		return "解读影响"
	case hasAny(text, "讨论", "热议", "网友"):
		return "舆论观察"
	default:
		return "补充视角"
	}
}

func narrativeDifferenceHint(view SourceView) string {
	if view.Focus == "权威处置" {
		return "更适合作为事实锚点。"
	}
	if view.Focus == "公众讨论" {
		return "更能反映舆论反应，但需要事实源交叉验证。"
	}
	if view.Focus == "影响分析" {
		return "更关注事件可能带来的后续影响。"
	}
	return "提供与其他来源不同的补充角度。"
}

func buildControversyBrief(detail EventDetail) ControversyBrief {
	signals := controversySignals(detail)
	hasRumor := hasRumorSignal(detail)
	level := "none"
	if hasRumor || strings.Contains(detail.Event.DisplayQualityReason, "mixed_unrelated_sources") {
		level = "high"
	} else if len(signals) >= 2 || detail.Event.Status == "monitoring" || detail.Event.DisplayQualityLevel == "weak" {
		level = "medium"
	} else if len(signals) == 1 {
		level = "low"
	}
	return ControversyBrief{
		Level:          level,
		Title:          controversyTitle(level, hasRumor),
		Summary:        controversySummary(level, signals, hasRumor),
		Signals:        signals,
		ActionHint:     controversyActionHint(level, hasRumor),
		HasRumorSignal: hasRumor,
	}
}

func controversySignals(detail EventDetail) []string {
	signals := []string{}
	text := controversyText(detail)
	if hasAny(text, "辟谣", "假的", "传言", "谣言", "网传", "核验") {
		signals = append(signals, "出现传言或辟谣信号")
	}
	if hasAny(text, "反转", "争议", "否认", "澄清", "回应", "质疑") {
		signals = append(signals, "叙事可能存在争议或反转")
	}
	if detail.Event.SourceCount <= 1 {
		signals = append(signals, "当前仍是单一来源")
	}
	if detail.EvidenceChain.WeakSourceCount > 0 || strings.Contains(detail.Event.DisplayQualityReason, "missing") {
		signals = append(signals, "证据链仍有缺口")
	}
	if strings.Contains(detail.Event.DisplayQualityReason, "mixed_unrelated_sources") {
		signals = append(signals, "来源疑似串台")
	}
	return uniqueFirstN(signals, 4)
}

func hasRumorSignal(detail EventDetail) bool {
	return hasAny(controversyText(detail), "辟谣", "假的", "传言", "谣言", "网传", "核验")
}

func controversyText(detail EventDetail) string {
	parts := []string{
		detail.Event.Title,
		detail.Event.OneLineSummary,
		summaryValue(detail.Summaries, "risk_notice", "风险提示"),
		summaryValue(detail.Summaries, "what_happened", "发生了什么"),
	}
	for _, source := range detail.RepresentativeSources {
		parts = append(parts, source.Title)
	}
	return strings.Join(parts, " ")
}

func hasAny(text string, markers ...string) bool {
	for _, marker := range markers {
		if strings.Contains(text, marker) {
			return true
		}
	}
	return false
}

func controversyTitle(level string, hasRumor bool) string {
	if hasRumor {
		return "传言核验中"
	}
	switch level {
	case "high":
		return "高争议风险"
	case "medium":
		return "需要继续核验"
	case "low":
		return "存在轻微信息缺口"
	default:
		return "暂未发现明显争议"
	}
}

func controversySummary(level string, signals []string, hasRumor bool) string {
	if hasRumor {
		return "该事件包含传言、辟谣或核验信号，当前更适合等待权威来源确认。"
	}
	if level == "none" {
		return "当前未发现明显传言、反转或来源串台信号。"
	}
	if len(signals) == 0 {
		return "当前信息仍需继续观察。"
	}
	return "当前需要留意：" + strings.Join(signals, "、") + "。"
}

func controversyActionHint(level string, hasRumor bool) string {
	if hasRumor || level == "high" {
		return "不要只看标题转述，优先等待官方或权威媒体确认。"
	}
	if level == "medium" {
		return "适合继续跟踪，暂不宜当作完整事实下结论。"
	}
	if level == "low" {
		return "可以阅读，但后续来源补强后再判断影响。"
	}
	return "可按当前事实阅读，同时留意后续新增来源。"
}

func buildEvidenceChain(sources []RepresentativeSource) EvidenceChain {
	chain := EvidenceChain{
		EvidenceSources: []EvidenceSource{},
		WeakSources:     []EvidenceSource{},
		PlatformViews:   []PlatformView{},
	}
	platformCounts := map[string]int{}
	for index, source := range sources {
		evidence := evidenceSourceFromRepresentative(source, 100-index*8)
		platformCounts[source.ChannelName]++
		if isUsableEvidence(source) {
			chain.EvidenceSources = append(chain.EvidenceSources, evidence)
			chain.UsableSourceCount++
		} else {
			chain.WeakSources = append(chain.WeakSources, evidence)
			chain.WeakSourceCount++
		}
	}
	for _, source := range sources {
		channelName := strings.TrimSpace(source.ChannelName)
		if channelName == "" || platformCounts[channelName] <= 0 {
			continue
		}
		chain.PlatformViews = append(chain.PlatformViews, PlatformView{
			ChannelName: channelName,
			SourceCount: platformCounts[channelName],
		})
		delete(platformCounts, channelName)
	}
	return chain
}

func evidenceSourceFromRepresentative(source RepresentativeSource, weight int) EvidenceSource {
	level, summary, reasons := sourceQuality(source)
	return EvidenceSource{
		InfoID:            source.InfoID,
		Title:             source.Title,
		ChannelName:       source.ChannelName,
		SourceURL:         source.SourceURL,
		Weight:            weight,
		DetailScore:       source.DetailScore,
		DetailFetchStatus: source.DetailFetchStatus,
		QualityLevel:      level,
		QualitySummary:    summary,
		RiskReasons:       reasons,
	}
}

func isUsableEvidence(source RepresentativeSource) bool {
	status := strings.TrimSpace(source.DetailFetchStatus)
	return (status == "complete" && source.DetailScore >= 70) || (status == "partial" && source.DetailScore >= 60)
}

func sourceQuality(source RepresentativeSource) (string, string, []string) {
	status := strings.TrimSpace(source.DetailFetchStatus)
	reasons := []string{}
	if status == "" || status == "pending" || status == "list_only" || status == "failed" {
		reasons = append(reasons, "detail_not_complete")
	}
	if source.DetailScore < 60 {
		reasons = append(reasons, "low_detail_score")
	}
	if source.DetailContentLength > 0 && source.DetailContentLength < 80 {
		reasons = append(reasons, "short_content")
	}
	if isUsableEvidence(source) {
		if status == "complete" && source.DetailScore >= 85 {
			return "高", "来源正文完整，详情质量较高，可作为主要证据。", reasons
		}
		return "可用", "来源信息可用，但仍适合结合其他渠道交叉验证。", reasons
	}
	if len(reasons) == 0 {
		reasons = append(reasons, "needs_cross_check")
	}
	return "谨慎", humanizeEvidenceReasons(reasons), reasons
}

func humanizeEvidenceReasons(reasons []string) string {
	labels := map[string]string{
		"detail_not_complete": "来源详情不完整",
		"low_detail_score":    "详情评分偏低",
		"short_content":       "正文信息量偏少",
		"needs_cross_check":   "需要更多来源交叉验证",
	}
	result := make([]string, 0, len(reasons))
	for _, reason := range reasons {
		if label, ok := labels[reason]; ok {
			result = append(result, label)
		} else {
			result = append(result, reason)
		}
	}
	return strings.Join(result, "，") + "。"
}

func buildIntelligenceBrief(detail EventDetail) IntelligenceBrief {
	event := detail.Event
	stage := intelligenceStage(event)
	questions := followUpQuestions(detail)
	return IntelligenceBrief{
		Stage:             stage,
		ConfidenceReason:  confidenceReason(event),
		DecisionHint:      decisionHint(event),
		FollowUpQuestions: questions,
	}
}

func intelligenceStage(event EventCore) string {
	if event.Status == "monitoring" || event.DisplayQualityLevel == "weak" {
		return "观察中"
	}
	switch event.EvolutionStage {
	case "spreading":
		return "扩散中"
	case "reversal":
		return "可能反转"
	case "cooling":
		return "降温中"
	}
	if event.SourceCount >= 3 {
		return "多源确认"
	}
	if event.SourceCount <= 1 {
		return "单源待核验"
	}
	return "持续发酵"
}

func confidenceReason(event EventCore) string {
	if event.Status == "monitoring" || event.DisplayQualityLevel == "weak" {
		if strings.TrimSpace(event.DisplayQualityReason) != "" {
			return "当前证据仍不充分：" + humanizeQualityReasons(event.DisplayQualityReason)
		}
		return "当前仍处于观察中，事实来源和后续进展还需要继续补充。"
	}
	if event.SourceCount >= 3 {
		return "事件已出现多来源交叉验证，且通过可信流展示质量门槛。"
	}
	if event.SourceCount == 2 {
		return "事件已有两个来源跟进，适合继续观察不同来源叙事是否一致。"
	}
	return "事件当前主要来自单一来源，结论需要等待更多事实源验证。"
}

func decisionHint(event EventCore) string {
	if event.Status == "monitoring" || event.DisplayQualityLevel == "weak" {
		return "先关注，不急于下结论。"
	}
	if event.SourceCount >= 3 {
		return "值得阅读详情，可作为今日重点事件跟踪。"
	}
	return "可以快速了解，但仍需留意后续来源补强。"
}

func followUpQuestions(detail EventDetail) []string {
	event := detail.Event
	questions := make([]string, 0, 3)
	if event.SourceCount <= 1 {
		questions = append(questions, "是否出现第二个独立来源交叉验证？")
	}
	if strings.TrimSpace(summaryValue(detail.Summaries, "risk_notice", "风险提示")) != "" || strings.Contains(event.DisplayQualityReason, "missing") {
		questions = append(questions, "后续是否有官方、权威媒体或当事方进一步确认？")
	}
	switch event.PrimaryCategory.Code {
	case "hot", "international":
		questions = append(questions, "事件会继续扩散、反转，还是快速降温？")
	case "economy":
		questions = append(questions, "这件事会影响哪些市场、行业或普通用户决策？")
	case "sports":
		questions = append(questions, "赛程、人员或结果是否还有后续变化？")
	case "tech", "ai":
		questions = append(questions, "技术进展是否会影响产品、产业链或开发者生态？")
	default:
		questions = append(questions, "这件事为什么值得继续关注？")
	}
	questions = append(questions, "不同平台的叙事是否出现明显差异？")
	return uniqueFirstN(questions, 3)
}

func summaryValue(summaries map[string]string, keys ...string) string {
	for _, key := range keys {
		if value := strings.TrimSpace(summaries[key]); value != "" {
			return value
		}
	}
	return ""
}

func uniqueFirstN(values []string, limit int) []string {
	result := make([]string, 0, limit)
	seen := map[string]struct{}{}
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value == "" {
			continue
		}
		if _, ok := seen[value]; ok {
			continue
		}
		seen[value] = struct{}{}
		result = append(result, value)
		if len(result) >= limit {
			break
		}
	}
	return result
}

func humanizeQualityReasons(reasonText string) string {
	labels := map[string]string{
		"empty_sources":                     "暂缺可核验来源",
		"single_weak_source":                "当前只有单一弱来源",
		"low_value_content":                 "来源内容价值偏低",
		"social_signal_without_fact_source": "社交热度尚未得到事实源确认",
		"missing_complete_source":           "缺少完整详情来源",
		"missing_usable_source":             "缺少可用事实来源",
		"mixed_unrelated_sources":           "来源疑似串台",
	}
	parts := strings.Split(reasonText, ",")
	result := make([]string, 0, len(parts))
	for _, part := range parts {
		part = strings.TrimSpace(part)
		if part == "" {
			continue
		}
		if label, ok := labels[part]; ok {
			result = append(result, label)
		} else {
			result = append(result, part)
		}
	}
	if len(result) == 0 {
		return reasonText
	}
	return strings.Join(result, "、")
}
