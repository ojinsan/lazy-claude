package lark

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	"fund-manager/internal/model"
)

type Config struct {
	AppID      string
	AppSecret  string
	SheetToken string
	Range      string
	WikiToken  string
	HTTPClient *http.Client
	APIBase    string // optional override, defaults to Feishu then LarkSuite fallback
}

type Client struct {
	appID      string
	appSecret  string
	sheetToken string
	rangeRef   string
	wikiToken  string
	httpClient *http.Client
	apiBase    string

	mu          sync.RWMutex
	tenantToken string
	tokenExpiry time.Time
}

func New(cfg Config) *Client {
	httpClient := cfg.HTTPClient
	if httpClient == nil {
		httpClient = &http.Client{Timeout: 10 * time.Second}
	}

	apiBase := strings.TrimSpace(cfg.APIBase)
	if apiBase == "" {
		apiBase = "https://open.feishu.cn"
	}

	return &Client{
		appID:      strings.TrimSpace(cfg.AppID),
		appSecret:  strings.TrimSpace(cfg.AppSecret),
		sheetToken: strings.TrimSpace(cfg.SheetToken),
		rangeRef:   defaultString(strings.TrimSpace(cfg.Range), "Sheet1!A:B"),
		wikiToken:  strings.TrimSpace(cfg.WikiToken),
		httpClient: httpClient,
		apiBase:    apiBase,
	}
}

func (c *Client) Configured() bool {
	return c != nil && c.appID != "" && c.appSecret != "" && (c.sheetToken != "" || c.wikiToken != "")
}

func (c *Client) FetchWatchlist(ctx context.Context) ([]model.WatchlistEntry, error) {
	if c == nil {
		return nil, errors.New("lark client is nil")
	}
	if !c.Configured() {
		return nil, errors.New("lark client not configured")
	}

	fmt.Printf("[lark] FetchWatchlist: wikiToken=%s, sheetToken=%s, apiBase=%s\n", c.wikiToken, c.sheetToken, c.apiBase)

	// getSheetToken will discover the correct host and cache the token
	sheetToken, err := c.getSheetToken(ctx, "")
	if err != nil {
		return nil, fmt.Errorf("getSheetToken: %w", err)
	}
	fmt.Printf("[lark] resolved sheetToken=%s, apiBase=%s\n", sheetToken, c.apiBase)

	// Get token (will use cached token from getSheetToken or fetch new one)
	token, err := c.getTenantToken(ctx)
	if err != nil {
		return nil, fmt.Errorf("getTenantToken: %w", err)
	}
	fmt.Printf("[lark] got tenantToken (len=%d)\n", len(token))

	rangeEscaped := url.PathEscape(c.rangeRef)
	endpoint := fmt.Sprintf("%s/open-apis/sheets/v2/spreadsheets/%s/values/%s", c.apiBase, sheetToken, rangeEscaped)
	fmt.Printf("[lark] calling sheet endpoint: %s\n", endpoint)

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint, nil)
	if err != nil {
		return nil, fmt.Errorf("build request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("call lark sheet: %w", err)
	}
	defer resp.Body.Close()

	var body struct {
		Code int    `json:"code"`
		Msg  string `json:"msg"`
		Data struct {
			ValueRange struct {
				Values [][]string `json:"values"`
			} `json:"valueRange"`
		} `json:"data"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
		return nil, fmt.Errorf("decode lark sheet response: %w", err)
	}
	if body.Code != 0 {
		return nil, fmt.Errorf("lark sheet error: %s (code=%d)", body.Msg, body.Code)
	}

	rows := body.Data.ValueRange.Values
	if len(rows) == 0 {
		return nil, nil
	}

	// Skip header row if it looks like one.
	startIdx := 0
	if len(rows[0]) >= 2 && isHeader(rows[0][0]) && isHeader(rows[0][1]) {
		startIdx = 1
	}

	var out []model.WatchlistEntry
	for _, row := range rows[startIdx:] {
		if len(row) < 2 {
			continue
		}
		stock := strings.TrimSpace(row[0])
		status := strings.TrimSpace(row[1])
		if stock == "" && status == "" {
			continue
		}
		out = append(out, model.WatchlistEntry{
			Stock:  stock,
			Status: status,
		})
	}
	return out, nil
}

func (c *Client) getTenantToken(ctx context.Context) (string, error) {
	c.mu.RLock()
	if c.tenantToken != "" && time.Now().Before(c.tokenExpiry) {
		defer c.mu.RUnlock()
		return c.tenantToken, nil
	}
	c.mu.RUnlock()

	c.mu.Lock()
	defer c.mu.Unlock()
	if c.tenantToken != "" && time.Now().Before(c.tokenExpiry) {
		return c.tenantToken, nil
	}

	payload, err := json.Marshal(map[string]string{
		"app_id":     c.appID,
		"app_secret": c.appSecret,
	})
	if err != nil {
		return "", err
	}

	// Use c.apiBase for consistent host usage (defaults to Feishu)
	tokenURL := fmt.Sprintf("%s/open-apis/auth/v3/tenant_access_token/internal/", c.apiBase)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, tokenURL, bytes.NewReader(payload))
	if err != nil {
		return "", fmt.Errorf("build tenant token request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("get tenant token: %w", err)
	}
	defer resp.Body.Close()

	var body struct {
		Code              int    `json:"code"`
		Msg               string `json:"msg"`
		TenantAccessToken string `json:"tenant_access_token"`
		Expire            int    `json:"expire"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
		return "", fmt.Errorf("decode tenant token: %w", err)
	}
	if body.Code != 0 || body.TenantAccessToken == "" {
		return "", fmt.Errorf("tenant token error: %s (code=%d)", body.Msg, body.Code)
	}

	expiry := time.Now().Add(time.Duration(body.Expire-60) * time.Second)
	c.tenantToken = body.TenantAccessToken
	c.tokenExpiry = expiry

	return c.tenantToken, nil
}

func isHeader(val string) bool {
	v := strings.ToLower(strings.TrimSpace(val))
	return strings.Contains(v, "stock") || strings.Contains(v, "status")
}

func (c *Client) getSheetToken(ctx context.Context, _ string) (string, error) {
	c.mu.RLock()
	if c.sheetToken != "" {
		defer c.mu.RUnlock()
		return c.sheetToken, nil
	}
	c.mu.RUnlock()

	if c.wikiToken == "" {
		return "", errors.New("sheet token missing and wiki token not set")
	}

	c.mu.Lock()
	defer c.mu.Unlock()
	if c.sheetToken != "" {
		return c.sheetToken, nil
	}

	// Resolve wiki node -> sheet token via metainfo endpoint.
	// Try each host with its own token (can't use token from one host on another).
	hosts := []string{"https://open.feishu.cn", "https://open.larksuite.com"}
	// Prefer the configured apiBase first if provided.
	if c.apiBase != "" && c.apiBase != hosts[0] && c.apiBase != hosts[1] {
		hosts = append([]string{c.apiBase}, hosts...)
	}

	var lastErr error
	for _, host := range hosts {
		// Get a token specifically for this host
		hostToken, tokenErr := c.getTenantTokenForHost(ctx, host)
		if tokenErr != nil {
			lastErr = fmt.Errorf("get token for %s: %w", host, tokenErr)
			continue
		}

		endpoint := fmt.Sprintf("%s/open-apis/wiki/v2/spaces/get_node?token=%s", host, url.QueryEscape(c.wikiToken))
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint, nil)
		if err != nil {
			lastErr = fmt.Errorf("build wiki get_node request: %w", err)
			continue
		}
		req.Header.Set("Authorization", "Bearer "+hostToken)
		req.Header.Set("Content-Type", "application/json")

		resp, err := c.httpClient.Do(req)
		if err != nil {
			lastErr = fmt.Errorf("wiki get_node (%s): %w", host, err)
			continue
		}
		raw, readErr := io.ReadAll(resp.Body)
		resp.Body.Close()
		if readErr != nil {
			lastErr = fmt.Errorf("read wiki get_node (%s): %w", host, readErr)
			continue
		}

		var body struct {
			Code int    `json:"code"`
			Msg  string `json:"msg"`
			Data struct {
				Node struct {
					ObjToken string `json:"obj_token"`
					ObjType  string `json:"obj_type"`
				} `json:"node"`
			} `json:"data"`
		}
		if err := json.Unmarshal(raw, &body); err != nil {
			lastErr = fmt.Errorf("decode wiki get_node (%s): %w body=%s", host, err, string(raw))
			continue
		}
		if body.Code != 0 {
			lastErr = fmt.Errorf("wiki get_node error (%s): %s (code=%d)", host, body.Msg, body.Code)
			continue
		}
		objToken := body.Data.Node.ObjToken
		objType := strings.ToLower(body.Data.Node.ObjType)
		if objToken == "" {
			lastErr = fmt.Errorf("wiki get_node missing obj_token (%s)", host)
			continue
		}
		if !strings.Contains(objType, "sheet") {
			lastErr = fmt.Errorf("wiki node is not a sheet (type=%s) (%s)", body.Data.Node.ObjType, host)
			continue
		}

		// The wiki token is the spreadsheet token, objToken is the sheet ID
		// Store the objToken as sheetId for range reference
		c.sheetToken = c.wikiToken
		// Update apiBase to the working host and cache the token
		c.apiBase = host
		c.tenantToken = hostToken
		c.tokenExpiry = time.Now().Add(110 * time.Minute) // Conservative expiry
		return c.sheetToken, nil
	}

	if lastErr != nil {
		return "", lastErr
	}
	return c.sheetToken, nil
}

// getTenantTokenForHost gets a token from a specific host without caching
func (c *Client) getTenantTokenForHost(ctx context.Context, host string) (string, error) {
	fmt.Printf("[lark] getTenantTokenForHost: trying host=%s\n", host)
	payload, err := json.Marshal(map[string]string{
		"app_id":     c.appID,
		"app_secret": c.appSecret,
	})
	if err != nil {
		return "", err
	}

	tokenURL := fmt.Sprintf("%s/open-apis/auth/v3/tenant_access_token/internal/", host)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, tokenURL, bytes.NewReader(payload))
	if err != nil {
		return "", fmt.Errorf("build tenant token request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("get tenant token: %w", err)
	}
	defer resp.Body.Close()

	var body struct {
		Code              int    `json:"code"`
		Msg               string `json:"msg"`
		TenantAccessToken string `json:"tenant_access_token"`
		Expire            int    `json:"expire"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
		return "", fmt.Errorf("decode tenant token: %w", err)
	}
	fmt.Printf("[lark] getTenantTokenForHost: host=%s code=%d msg=%s tokenLen=%d\n", host, body.Code, body.Msg, len(body.TenantAccessToken))
	if body.Code != 0 || body.TenantAccessToken == "" {
		return "", fmt.Errorf("tenant token error: %s (code=%d)", body.Msg, body.Code)
	}

	return body.TenantAccessToken, nil
}

func defaultString(val, fallback string) string {
	if val != "" {
		return val
	}
	return fallback
}
