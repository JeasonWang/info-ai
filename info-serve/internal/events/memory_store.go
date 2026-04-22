package events

import "context"

// MemoryStore 是本地开发和路由测试使用的事件空存储。
type MemoryStore struct{}

func NewMemoryStore() *MemoryStore {
	return &MemoryStore{}
}

func (s *MemoryStore) ListEvents(ctx context.Context, params ListEventsParams) (EventPage, error) {
	return EventPage{Total: 0, Page: params.Page, PageSize: params.PageSize, Items: []EventListItem{}}, nil
}

func (s *MemoryStore) GetEventDetail(ctx context.Context, id int64) (EventDetail, error) {
	return EventDetail{
		Event:                 EventCore{ID: id},
		Timeline:              []TimelineItem{},
		Summaries:             map[string]string{},
		SourceViews:           []SourceView{},
		RepresentativeSources: []RepresentativeSource{},
		TechContext:           TechContext{Topics: []TechTopic{}, Entities: []string{}, Keywords: []string{}},
	}, nil
}
