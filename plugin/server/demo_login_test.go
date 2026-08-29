package main

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/mattermost/mattermost/server/public/model"
	"github.com/mattermost/mattermost/server/public/plugin/plugintest"
	"github.com/stretchr/testify/mock"
	"github.com/stretchr/testify/require"
)

func TestDemoLoginCreatesShortLivedNonAdminSession(t *testing.T) {
	api := &plugintest.API{}
	user := &model.User{
		Id:       model.NewId(),
		Username: "maya",
		Roles:    model.SystemUserRoleId,
	}
	api.On("GetUserByUsername", "maya").Return(user, (*model.AppError)(nil)).Once()
	api.On("CreateSession", mock.MatchedBy(func(session *model.Session) bool {
		return session.UserId == user.Id &&
			session.Roles == user.Roles &&
			session.ExpiresAt > model.GetMillis() &&
			session.Props[model.SessionPropType] == "nobs_public_demo"
	})).Return(&model.Session{Token: model.NewId()}, (*model.AppError)(nil)).Once()
	defer api.AssertExpectations(t)

	p := &Plugin{configuration: &configuration{PublicDemoLogin: true, DemoLoginUsername: "maya"}}
	p.SetAPI(api)
	request := httptest.NewRequest(http.MethodPost, "http://localhost:8065/plugins/com.noping.enterprise/api/v1/demo-login", nil)
	request.Header.Set("Origin", "http://localhost:8065")
	response := httptest.NewRecorder()

	p.handleDemoLogin(response, request)

	require.Equal(t, http.StatusSeeOther, response.Code)
	require.Equal(t, "/acme/channels/project-atlas", response.Header().Get("Location"))
	cookies := response.Result().Cookies()
	require.Len(t, cookies, 2)
	require.Equal(t, model.SessionCookieToken, cookies[0].Name)
	require.True(t, cookies[0].HttpOnly)
	require.Equal(t, model.SessionCookieUser, cookies[1].Name)
	require.False(t, cookies[1].HttpOnly)
}

func TestDemoLoginRejectsCrossOriginRequests(t *testing.T) {
	p := &Plugin{configuration: &configuration{PublicDemoLogin: true, DemoLoginUsername: "maya"}}
	request := httptest.NewRequest(http.MethodPost, "http://localhost:8065/plugins/com.noping.enterprise/api/v1/demo-login", nil)
	request.Header.Set("Origin", "https://example.invalid")
	response := httptest.NewRecorder()

	p.handleDemoLogin(response, request)

	require.Equal(t, http.StatusForbidden, response.Code)
}

func TestDemoLoginPreservesSafeLocalRedirect(t *testing.T) {
	api := &plugintest.API{}
	user := &model.User{Id: model.NewId(), Username: "maya", Roles: model.SystemUserRoleId}
	api.On("GetUserByUsername", "maya").Return(user, (*model.AppError)(nil)).Once()
	api.On("CreateSession", mock.AnythingOfType("*model.Session")).Return(&model.Session{Token: model.NewId()}, (*model.AppError)(nil)).Once()
	defer api.AssertExpectations(t)

	p := &Plugin{configuration: &configuration{PublicDemoLogin: true, DemoLoginUsername: "maya"}}
	p.SetAPI(api)
	request := httptest.NewRequest(http.MethodPost, "https://nobs.example/plugins/com.noping.enterprise/api/v1/demo-login?redirect_to=%2Facme%2Fnobs%2Fcalendar", nil)
	request.Header.Set("Origin", "https://nobs.example")
	response := httptest.NewRecorder()

	p.handleDemoLogin(response, request)

	require.Equal(t, http.StatusSeeOther, response.Code)
	require.Equal(t, "/acme/nobs/calendar", response.Header().Get("Location"))
}

func TestDemoLoginRejectsExternalRedirect(t *testing.T) {
	request := httptest.NewRequest(http.MethodPost, "https://nobs.example/plugins/com.noping.enterprise/api/v1/demo-login?redirect_to=https%3A%2F%2Fevil.example", nil)
	require.Equal(t, "/acme/channels/project-atlas", demoLoginRedirect(request))
}

func TestDemoLoginRejectsAdministratorAccount(t *testing.T) {
	api := &plugintest.API{}
	user := &model.User{
		Id:       model.NewId(),
		Username: "maya",
		Roles:    model.SystemUserRoleId + " " + model.SystemAdminRoleId,
	}
	api.On("GetUserByUsername", "maya").Return(user, (*model.AppError)(nil)).Once()
	defer api.AssertExpectations(t)

	p := &Plugin{configuration: &configuration{PublicDemoLogin: true, DemoLoginUsername: "maya"}}
	p.SetAPI(api)
	request := httptest.NewRequest(http.MethodPost, "https://nobs.example/plugins/com.noping.enterprise/api/v1/demo-login", nil)
	request.Header.Set("Origin", "https://nobs.example")
	response := httptest.NewRecorder()

	p.handleDemoLogin(response, request)

	require.Equal(t, http.StatusForbidden, response.Code)
}
