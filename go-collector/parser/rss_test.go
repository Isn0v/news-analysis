package parser

import (
	"strings"
	"testing"
	"time"

	"github.com/mmcdole/gofeed"
	ext "github.com/mmcdole/gofeed/extensions"
)

func TestStripUTM(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			name:     "Removes UTM parameters",
			input:    "https://coindesk.com/markets/2026/01/15/btc-rallies?utm_source=twitter&utm_medium=social&id=42",
			expected: "https://coindesk.com/markets/2026/01/15/btc-rallies?id=42",
		},
		{
			name:     "Removes Yahoo yptr parameter",
			input:    "https://finance.yahoo.com/news/crypto-update.html?yptr=yahoo",
			expected: "https://finance.yahoo.com/news/crypto-update.html",
		},
		{
			name:     "Preserves clean URL without query params",
			input:    "https://cointelegraph.com/news/ethereum-upgrade",
			expected: "https://cointelegraph.com/news/ethereum-upgrade",
		},
		{
			name:     "Handles empty string gracefully",
			input:    "",
			expected: "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			actual := StripUTM(tt.input)
			if actual != tt.expected {
				t.Errorf("StripUTM(%q) = %q; want %q", tt.input, actual, tt.expected)
			}
		})
	}
}

func TestExtractAuthors(t *testing.T) {
	t.Run("Extracts from DublinCoreExt and strips Cointelegraph prefix", func(t *testing.T) {
		item := &gofeed.Item{
			DublinCoreExt: &ext.DublinCoreExtension{
				Creator: []string{"Cointelegraph by John Doe", "Jane Smith"},
			},
		}

		authors := ExtractAuthors(item)
		if len(authors) != 2 {
			t.Fatalf("expected 2 authors, got %d", len(authors))
		}
		if authors[0] != "John Doe" {
			t.Errorf("expected 'John Doe', got %q", authors[0])
		}
		if authors[1] != "Jane Smith" {
			t.Errorf("expected 'Jane Smith', got %q", authors[1])
		}
	})

	t.Run("Extracts from item.Authors", func(t *testing.T) {
		item := &gofeed.Item{
			Authors: []*gofeed.Person{
				{Name: "Alice Cooper"},
			},
		}

		authors := ExtractAuthors(item)
		if len(authors) != 1 || authors[0] != "Alice Cooper" {
			t.Errorf("expected ['Alice Cooper'], got %v", authors)
		}
	})

	t.Run("Returns nil when no authors present", func(t *testing.T) {
		item := &gofeed.Item{}
		authors := ExtractAuthors(item)
		if authors != nil {
			t.Errorf("expected nil, got %v", authors)
		}
	})
}

func TestExtractImageURL(t *testing.T) {
	t.Run("Extracts from item.Image", func(t *testing.T) {
		item := &gofeed.Item{
			Image: &gofeed.Image{
				URL: "https://example.com/image.png",
			},
		}
		if img := ExtractImageURL(item); img != "https://example.com/image.png" {
			t.Errorf("expected 'https://example.com/image.png', got %q", img)
		}
	})

	t.Run("Extracts from Enclosures", func(t *testing.T) {
		item := &gofeed.Item{
			Enclosures: []*gofeed.Enclosure{
				{
					URL:  "https://example.com/cover.jpg",
					Type: "image/jpeg",
				},
			},
		}
		if img := ExtractImageURL(item); img != "https://example.com/cover.jpg" {
			t.Errorf("expected 'https://example.com/cover.jpg', got %q", img)
		}
	})
}

func TestParseFeedXML(t *testing.T) {
	xmlData := `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>Crypto News Daily</title>
    <link>https://example.com</link>
    <description>Daily crypto news</description>
    <item>
      <title>Bitcoin Hits New All-Time High</title>
      <link>https://example.com/news/1?utm_source=feed</link>
      <guid>guid-12345</guid>
      <pubDate>Thu, 15 Jan 2026 12:00:00 GMT</pubDate>
      <dc:creator>Satoshi Nakamoto</dc:creator>
      <category>Bitcoin</category>
      <category>Markets</category>
      <description>Summary of bitcoin surge</description>
      <content:encoded><![CDATA[<p>Full detailed report about the Bitcoin rally to new peaks.</p>]]></content:encoded>
    </item>
  </channel>
</rss>`

	fp := gofeed.NewParser()
	feed, err := fp.ParseString(xmlData)
	if err != nil {
		t.Fatalf("ParseString failed: %v", err)
	}

	if len(feed.Items) != 1 {
		t.Fatalf("expected 1 item, got %d", len(feed.Items))
	}

	item := feed.Items[0]
	if item.Title != "Bitcoin Hits New All-Time High" {
		t.Errorf("unexpected title: %s", item.Title)
	}

	cleanURL := StripUTM(item.Link)
	if cleanURL != "https://example.com/news/1" {
		t.Errorf("expected clean URL https://example.com/news/1, got %s", cleanURL)
	}

	authors := ExtractAuthors(item)
	if len(authors) != 1 || authors[0] != "Satoshi Nakamoto" {
		t.Errorf("expected author Satoshi Nakamoto, got %v", authors)
	}

	if !strings.Contains(item.Content, "Full detailed report") {
		t.Errorf("expected full content from content:encoded, got %s", item.Content)
	}

	if len(item.Categories) != 2 {
		t.Errorf("expected 2 categories, got %d", len(item.Categories))
	}

	expectedTime := time.Date(2026, 1, 15, 12, 0, 0, 0, time.UTC)
	if !item.PublishedParsed.UTC().Equal(expectedTime) {
		t.Errorf("expected published time %v, got %v", expectedTime, item.PublishedParsed)
	}
}
