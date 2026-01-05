// RagApiClient.cs
// Client C# per chiamare DataPizzaRouge API da Blazor
//
// Setup in Program.cs (Blazor):
//   builder.Services.AddHttpClient<RagApiClient>(client => {
//       client.BaseAddress = new Uri("http://localhost:8000");
//   });
//
// Uso nei componenti:
//   @inject RagApiClient RagClient

using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;

namespace DataPizzaRouge.Client
{
    // === MODELS ===

    public class QueryRequest
    {
        public string Collection { get; set; } = string.Empty;
        public string Query { get; set; } = string.Empty;
        public int TopK { get; set; } = 5;
        public bool IncludeSources { get; set; } = true;
        public bool IncludeHistory { get; set; } = false;
    }

    public class QueryResponse
    {
        public string Answer { get; set; } = string.Empty;
        public string? Sources { get; set; }
        public int NumResults { get; set; }
        public int? TokensUsed { get; set; }
        public string Timestamp { get; set; } = string.Empty;
    }

    public class RetrievalResult
    {
        public object Id { get; set; } = null!;
        public float Score { get; set; }
        public string Text { get; set; } = string.Empty;
        public string Url { get; set; } = string.Empty;
        public string PageTitle { get; set; } = string.Empty;
        public int ChunkIndex { get; set; }
    }

    public class RetrievalRequest
    {
        public string Collection { get; set; } = string.Empty;
        public string Query { get; set; } = string.Empty;
        public int TopK { get; set; } = 5;
        public float? ScoreThreshold { get; set; }
    }

    public class CollectionInfo
    {
        public string Name { get; set; } = string.Empty;
        public int PointsCount { get; set; }
        public int VectorSize { get; set; }
        public string Distance { get; set; } = string.Empty;
        public string Status { get; set; } = string.Empty;
    }

    public class DomainInfo
    {
        public string Domain { get; set; } = string.Empty;
        public int PageCount { get; set; }
        public float TotalSizeMb { get; set; }
        public string? FirstCrawl { get; set; }
        public string? LastCrawl { get; set; }
    }

    public class HealthResponse
    {
        public string Status { get; set; } = string.Empty;
        public bool QdrantConnected { get; set; }
        public bool OpenaiConfigured { get; set; }
        public bool AnthropicConfigured { get; set; }
        public string Timestamp { get; set; } = string.Empty;
    }

    // === CLIENT ===

    public class RagApiClient
    {
        private readonly HttpClient _httpClient;

        public RagApiClient(HttpClient httpClient)
        {
            _httpClient = httpClient;
        }

        /// <summary>
        /// Esegue query RAG completa (retrieval + generazione risposta).
        /// </summary>
        public async Task<QueryResponse> QueryAsync(
            string collection,
            string query,
            int topK = 5,
            bool includeSources = true,
            bool includeHistory = false)
        {
            var request = new QueryRequest
            {
                Collection = collection,
                Query = query,
                TopK = topK,
                IncludeSources = includeSources,
                IncludeHistory = includeHistory
            };

            var response = await _httpClient.PostAsJsonAsync("/api/query", request);
            response.EnsureSuccessStatusCode();

            return await response.Content.ReadFromJsonAsync<QueryResponse>()
                ?? throw new Exception("Risposta null dall'API");
        }

        /// <summary>
        /// Esegue solo retrieval documenti (senza generazione).
        /// </summary>
        public async Task<List<RetrievalResult>> RetrievalAsync(
            string collection,
            string query,
            int topK = 5,
            float? scoreThreshold = null)
        {
            var request = new RetrievalRequest
            {
                Collection = collection,
                Query = query,
                TopK = topK,
                ScoreThreshold = scoreThreshold
            };

            var response = await _httpClient.PostAsJsonAsync("/api/retrieval", request);
            response.EnsureSuccessStatusCode();

            return await response.Content.ReadFromJsonAsync<List<RetrievalResult>>()
                ?? new List<RetrievalResult>();
        }

        /// <summary>
        /// Lista tutte le collection disponibili.
        /// </summary>
        public async Task<List<string>> GetCollectionsAsync()
        {
            return await _httpClient.GetFromJsonAsync<List<string>>("/api/collections")
                ?? new List<string>();
        }

        /// <summary>
        /// Ottiene informazioni su una collection specifica.
        /// </summary>
        public async Task<CollectionInfo> GetCollectionInfoAsync(string collectionName)
        {
            return await _httpClient.GetFromJsonAsync<CollectionInfo>($"/api/collections/{collectionName}")
                ?? throw new Exception($"Collection '{collectionName}' non trovata");
        }

        /// <summary>
        /// Lista tutti i domini crawlati disponibili.
        /// </summary>
        public async Task<List<string>> GetDomainsAsync()
        {
            return await _httpClient.GetFromJsonAsync<List<string>>("/api/domains")
                ?? new List<string>();
        }

        /// <summary>
        /// Ottiene informazioni su un dominio crawlato.
        /// </summary>
        public async Task<DomainInfo> GetDomainInfoAsync(string domain)
        {
            return await _httpClient.GetFromJsonAsync<DomainInfo>($"/api/domains/{domain}")
                ?? throw new Exception($"Dominio '{domain}' non trovato");
        }

        /// <summary>
        /// Health check - verifica stato API e servizi.
        /// </summary>
        public async Task<HealthResponse> GetHealthAsync()
        {
            return await _httpClient.GetFromJsonAsync<HealthResponse>("/health")
                ?? throw new Exception("Health check fallito");
        }

        /// <summary>
        /// Verifica se l'API è raggiungibile.
        /// </summary>
        public async Task<bool> IsApiAvailableAsync()
        {
            try
            {
                var response = await _httpClient.GetAsync("/");
                return response.IsSuccessStatusCode;
            }
            catch
            {
                return false;
            }
        }
    }
}
