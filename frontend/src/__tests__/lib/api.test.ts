import * as api from "@/lib/api";

// Mock fetch globally
global.fetch = jest.fn();

describe("API Client", () => {
  const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("fetchApplicants", () => {
    it("fetches applicants with default parameters", async () => {
      const mockResponse = {
        items: [
          {
            id: "1",
            name: "John Doe",
            email: "john@example.com",
            risk_level: "low",
          },
        ],
        total: 1,
        total_pages: 1,
        page: 1,
        page_size: 20,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await api.fetchApplicants();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/applicants?")
      );
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("page=1")
      );
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("page_size=20")
      );
      expect(result).toEqual(mockResponse);
    });

    it("applies filters correctly", async () => {
      const mockResponse = { items: [], total: 0, total_pages: 0, page: 1, page_size: 20 };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      await api.fetchApplicants({
        page: 2,
        pageSize: 50,
        sortBy: "name",
        sortOrder: "asc",
        riskLevel: "high",
        isReviewed: true,
        assignedTa: "John Smith",
        source: "LinkedIn",
        flagType: "VOIP_PHONE",
      });

      const callUrl = (mockFetch.mock.calls[0] as [string])[0];
      expect(callUrl).toContain("page=2");
      expect(callUrl).toContain("page_size=50");
      expect(callUrl).toContain("sort_by=name");
      expect(callUrl).toContain("sort_order=asc");
      expect(callUrl).toContain("risk_level=high");
      expect(callUrl).toContain("is_reviewed=true");
      expect(callUrl).toContain("assigned_ta=John+Smith");
      expect(callUrl).toContain("source=LinkedIn");
      expect(callUrl).toContain("flag_type=VOIP_PHONE");
    });

    it("throws error on failed fetch", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: "Internal Server Error",
      } as Response);

      await expect(api.fetchApplicants()).rejects.toThrow(
        "Failed to fetch applicants: Internal Server Error"
      );
    });
  });

  describe("fetchApplicant", () => {
    it("fetches single applicant by id", async () => {
      const mockApplicant = {
        id: "test-id",
        name: "John Doe",
        email: "john@example.com",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockApplicant,
      } as Response);

      const result = await api.fetchApplicant("test-id");

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/applicants/test-id")
      );
      expect(result).toEqual(mockApplicant);
    });

    it("throws not found error for 404", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      } as Response);

      await expect(api.fetchApplicant("invalid-id")).rejects.toThrow(
        "Applicant not found"
      );
    });

    it("throws generic error for other failures", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: "Server Error",
      } as Response);

      await expect(api.fetchApplicant("test-id")).rejects.toThrow(
        "Failed to fetch applicant: Server Error"
      );
    });
  });

  describe("updateApplicantReviewed", () => {
    it("updates applicant reviewed status", async () => {
      const mockUpdated = {
        id: "test-id",
        is_reviewed: true,
        reviewed_by: "Jane Doe",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUpdated,
      } as Response);

      const result = await api.updateApplicantReviewed("test-id", true, "Jane Doe");

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/applicants/test-id"),
        expect.objectContaining({
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            is_reviewed: true,
            reviewed_by: "Jane Doe",
          }),
        })
      );
      expect(result).toEqual(mockUpdated);
    });

    it("throws error on failed update", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: "Bad Request",
      } as Response);

      await expect(
        api.updateApplicantReviewed("test-id", true)
      ).rejects.toThrow("Failed to update applicant: Bad Request");
    });
  });

  describe("Sync API", () => {
    it("getSyncStatus returns sync status", async () => {
      const mockStatus = {
        status: "idle",
        progress: 0,
        total: 0,
        message: "No sync in progress",
        last_sync_at: null,
        last_sync_count: 0,
        error: null,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockStatus,
      } as Response);

      const result = await api.getSyncStatus();
      expect(result).toEqual(mockStatus);
    });

    it("startSync initiates a sync", async () => {
      const mockResponse = {
        message: "Sync started",
        status: "running",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await api.startSync(7);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/sync/start"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ days: 7 }),
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it("startSync throws conflict error when sync in progress", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 409,
      } as Response);

      await expect(api.startSync(7)).rejects.toThrow(
        "Sync already in progress"
      );
    });

    it("getApplicantCount returns count", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ count: 42 }),
      } as Response);

      const result = await api.getApplicantCount();
      expect(result.count).toBe(42);
    });
  });

  describe("Filter Options API", () => {
    it("getTAs returns list of TAs", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tas: ["TA 1", "TA 2"] }),
      } as Response);

      const result = await api.getTAs();
      expect(result).toEqual(["TA 1", "TA 2"]);
    });

    it("getSources returns list of sources", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ sources: ["LinkedIn", "Indeed"] }),
      } as Response);

      const result = await api.getSources();
      expect(result).toEqual(["LinkedIn", "Indeed"]);
    });

    it("getFlagTypes returns list of flag types", async () => {
      const mockFlagTypes = [
        { code: "VOIP_PHONE", name: "VoIP Phone", category: "phone" },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ flag_types: mockFlagTypes }),
      } as Response);

      const result = await api.getFlagTypes();
      expect(result).toEqual(mockFlagTypes);
    });

    it("getRiskLevels returns list of risk levels", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ risk_levels: ["low", "medium", "high"] }),
      } as Response);

      const result = await api.getRiskLevels();
      expect(result).toEqual(["low", "medium", "high"]);
    });
  });

  describe("Validation Rules API", () => {
    it("getValidationRules returns rules", async () => {
      const mockRules = {
        rules: [
          {
            name: "email_domain",
            description: "Checks email domain",
            category: "email",
            severity: "medium",
            version: "1.0",
            checks_fields: ["email"],
            trigger_examples: [],
            rationale: "Test",
            is_active: true,
          },
        ],
        total: 1,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockRules,
      } as Response);

      const result = await api.getValidationRules();
      expect(result).toEqual(mockRules);
    });
  });

  describe("Validation Data API - Disposable Domains", () => {
    it("getDisposableDomains returns domains with pagination", async () => {
      const mockResponse = {
        domains: ["temp-mail.com", "10minutemail.com"],
        total: 2,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await api.getDisposableDomains(100, 0);

      const callUrl = (mockFetch.mock.calls[0] as [string])[0];
      expect(callUrl).toContain("limit=100");
      expect(callUrl).toContain("offset=0");
      expect(result).toEqual(mockResponse);
    });

    it("addDisposableDomain adds a domain", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ domain: "spam.com", status: "added" }),
      } as Response);

      const result = await api.addDisposableDomain("spam.com", "Test note");

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/validation-data/disposable-domains"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ domain: "spam.com", notes: "Test note" }),
        })
      );
      expect(result.status).toBe("added");
    });

    it("removeDisposableDomain removes a domain", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ domain: "spam.com", status: "removed" }),
      } as Response);

      await api.removeDisposableDomain("spam.com");

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/validation-data/disposable-domains/spam.com"),
        expect.objectContaining({ method: "DELETE" })
      );
    });

    it("syncDisposableDomains triggers sync", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "started", message: "Sync initiated" }),
      } as Response);

      const result = await api.syncDisposableDomains();
      expect(result.status).toBe("started");
    });
  });

  describe("Integration Settings API", () => {
    it("getIntegrations returns list of integrations", async () => {
      const mockIntegrations = {
        integrations: [
          {
            provider: "ipqualityscore",
            display_name: "IP Quality Score",
            is_enabled: true,
            has_credentials: true,
            api_key_masked: "***abc123",
            api_secret_masked: null,
            account_id: null,
            fraud_score_threshold: 85,
            monthly_usage: 100,
            monthly_limit: 5000,
            last_test_at: null,
            last_test_success: null,
            last_test_message: null,
            notes: null,
            config_json: null,
          },
        ],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockIntegrations,
      } as Response);

      const result = await api.getIntegrations();
      expect(result).toEqual(mockIntegrations);
    });

    it("updateIntegration updates integration settings", async () => {
      const updateData = {
        is_enabled: true,
        api_key: "new-key", // pragma: allowlist secret
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ provider: "test", ...updateData }),
      } as Response);

      await api.updateIntegration("test", updateData);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/settings/integrations/test"),
        expect.objectContaining({
          method: "PATCH",
          body: JSON.stringify(updateData),
        })
      );
    });

    it("testIntegration tests integration", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, message: "Connection successful" }),
      } as Response);

      const result = await api.testIntegration("test");
      expect(result.success).toBe(true);
    });
  });

  describe("Re-validation API", () => {
    it("getRevalidateStatus returns status", async () => {
      const mockStatus = {
        status: "idle",
        progress: 0,
        total: 0,
        message: "No re-validation in progress",
        last_run_at: null,
        error: null,
        applicants_processed: 0,
        flags_raised: 0,
        flags_cleared: 0,
        risk_level_changes: 0,
        current_applicant_name: null,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockStatus,
      } as Response);

      const result = await api.getRevalidateStatus();
      expect(result).toEqual(mockStatus);
    });

    it("startRevalidation starts re-validation", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: "Started", status: "running" }),
      } as Response);

      const result = await api.startRevalidation({ days: 30, clear_existing_flags: true });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/revalidate/start"),
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining("30"),
        })
      );
      expect(result.status).toBe("running");
    });
  });

  describe("Admin API", () => {
    it("getDatabaseStats returns statistics", async () => {
      const mockStats = {
        applicants_count: 100,
        flags_count: 50,
        validation_runs_count: 10,
        flag_types_count: 15,
        linkedin_profiles_count: 80,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockStats,
      } as Response);

      const result = await api.getDatabaseStats();
      expect(result).toEqual(mockStats);
    });

    it("purgeDatabase purges data", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: "Purge started", status: "running" }),
      } as Response);

      const result = await api.purgeDatabase({ confirm: true, keep_flag_types: true });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/admin/purge"),
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining("true"),
        })
      );
      expect(result.status).toBe("running");
    });

    it("purgeDatabase throws error when confirm is missing", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
      } as Response);

      await expect(
        api.purgeDatabase({ confirm: false })
      ).rejects.toThrow("Must confirm purge operation");
    });
  });

  describe("Single Applicant Validation", () => {
    it("validateApplicant validates single applicant", async () => {
      const mockResponse = {
        applicant: { id: "test-id", name: "John" },
        rules_passed: 5,
        rules_failed: 2,
        rules_skipped: 0,
        flags_raised: 2,
        previous_risk_level: "low",
        new_risk_level: "medium",
        message: "Validation complete",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await api.validateApplicant("test-id");

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/applicants/test-id/validate"),
        expect.objectContaining({ method: "POST" })
      );
      expect(result).toEqual(mockResponse);
    });
  });
});
