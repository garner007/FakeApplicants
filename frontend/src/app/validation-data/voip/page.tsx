"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getVoIPCarriers,
  getVoIPAreaCodes,
  addVoIPCarrier,
  seedValidationData,
  type VoIPCarrier,
} from "@/lib/api";
import { Header } from "@/components/header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

function getConfidenceColor(confidence: string): string {
  switch (confidence) {
    case "high":
      return "bg-green-500";
    case "medium":
      return "bg-yellow-500";
    case "low":
      return "bg-gray-500";
    default:
      return "bg-gray-500";
  }
}

function getMatchTypeLabel(matchType: string): string {
  switch (matchType) {
    case "exact":
      return "Exact Match";
    case "substring":
      return "Contains";
    case "regex":
      return "Regex";
    default:
      return matchType;
  }
}

export default function VoIPPage() {
  const [carriers, setCarriers] = useState<VoIPCarrier[]>([]);
  const [areaCodes, setAreaCodes] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state for adding new carrier
  const [newCarrierName, setNewCarrierName] = useState("");
  const [newCarrierMatchType, setNewCarrierMatchType] = useState("substring");
  const [newCarrierConfidence, setNewCarrierConfidence] = useState("high");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [carriersResponse, areaCodesResponse] = await Promise.all([
        getVoIPCarriers(),
        getVoIPAreaCodes(),
      ]);
      setCarriers(carriersResponse.carriers);
      setAreaCodes(areaCodesResponse.area_codes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleAddCarrier = async () => {
    if (!newCarrierName.trim()) return;

    try {
      await addVoIPCarrier(
        newCarrierName.trim(),
        newCarrierMatchType,
        newCarrierConfidence
      );
      setNewCarrierName("");
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add carrier");
    }
  };

  const handleSeed = async () => {
    setSeeding(true);
    setError(null);
    try {
      await seedValidationData();
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to seed data");
    } finally {
      setSeeding(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <div className="container mx-auto py-8 px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">VoIP Detection Data</h1>
          <p className="text-gray-600 mt-2">
            Manage VoIP carrier patterns and area codes for phone validation.
          </p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md text-red-700">
            {error}
            <Button variant="outline" size="sm" className="ml-4" onClick={loadData}>
              Retry
            </Button>
          </div>
        )}

        <div className="grid gap-6 md:grid-cols-3 mb-6">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">VoIP Carriers</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-blue-600">
                {carriers.length}
              </div>
              <p className="text-sm text-gray-500">Carrier patterns</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">Area Codes</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-blue-600">
                {areaCodes.length}
              </div>
              <p className="text-sm text-gray-500">Known VoIP area codes</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <Button
                onClick={handleSeed}
                disabled={seeding}
                className="w-full"
                variant="outline"
              >
                {seeding ? "Seeding..." : "Seed Default Data"}
              </Button>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>VoIP Carriers</CardTitle>
              <CardDescription>
                Carrier names/patterns used to identify VoIP numbers
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="mb-4 p-4 bg-gray-50 rounded-md">
                <h4 className="font-medium mb-2">Add New Carrier Pattern</h4>
                <div className="grid gap-2">
                  <Input
                    placeholder="Carrier name or pattern"
                    value={newCarrierName}
                    onChange={(e) => setNewCarrierName(e.target.value)}
                  />
                  <div className="flex gap-2">
                    <Select
                      value={newCarrierMatchType}
                      onValueChange={setNewCarrierMatchType}
                    >
                      <SelectTrigger className="w-[140px]">
                        <SelectValue placeholder="Match Type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="substring">Contains</SelectItem>
                        <SelectItem value="exact">Exact Match</SelectItem>
                        <SelectItem value="regex">Regex</SelectItem>
                      </SelectContent>
                    </Select>
                    <Select
                      value={newCarrierConfidence}
                      onValueChange={setNewCarrierConfidence}
                    >
                      <SelectTrigger className="w-[120px]">
                        <SelectValue placeholder="Confidence" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="high">High</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="low">Low</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button
                      onClick={handleAddCarrier}
                      disabled={!newCarrierName.trim()}
                    >
                      Add
                    </Button>
                  </div>
                </div>
              </div>

              {loading ? (
                <div className="text-center py-8 text-gray-500">Loading...</div>
              ) : (
                <div className="border rounded-md max-h-[400px] overflow-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name/Pattern</TableHead>
                        <TableHead>Match Type</TableHead>
                        <TableHead>Confidence</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {carriers.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={3} className="text-center text-gray-500">
                            No carriers configured. Click &quot;Seed Default Data&quot; to add defaults.
                          </TableCell>
                        </TableRow>
                      ) : (
                        carriers.map((carrier) => (
                          <TableRow key={carrier.id}>
                            <TableCell className="font-mono text-sm">
                              {carrier.name}
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">
                                {getMatchTypeLabel(carrier.match_type)}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <Badge className={getConfidenceColor(carrier.confidence)}>
                                {carrier.confidence}
                              </Badge>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>VoIP Area Codes</CardTitle>
              <CardDescription>
                US area codes commonly associated with VoIP services
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
                <p className="text-sm text-blue-800">
                  <strong>Note:</strong> Area codes are only checked for US/Canada phone numbers
                  (country code +1). These codes are often used by VoIP providers but may also
                  have legitimate uses.
                </p>
              </div>

              {loading ? (
                <div className="text-center py-8 text-gray-500">Loading...</div>
              ) : (
                <div className="border rounded-md">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Area Code</TableHead>
                        <TableHead>Description</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {areaCodes.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={2} className="text-center text-gray-500">
                            No area codes configured. Click &quot;Seed Default Data&quot; to add defaults.
                          </TableCell>
                        </TableRow>
                      ) : (
                        areaCodes.map((code) => (
                          <TableRow key={code}>
                            <TableCell className="font-mono text-lg font-bold">
                              {code}
                            </TableCell>
                            <TableCell className="text-gray-600">
                              {code === "456" && "Inbound International"}
                              {code === "500" && "Personal Communications Services"}
                              {["521", "522", "533", "544", "566", "577", "588"].includes(code) &&
                                "Reserved / Non-geographic"}
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              )}

              <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-md">
                <h4 className="font-medium mb-2 text-green-900">🌟 IPQualityScore Integration (Recommended)</h4>
                <p className="text-sm text-green-800 mb-2">
                  For the most comprehensive VoIP detection with fraud scoring, enable IPQualityScore.
                  Includes VoIP detection, fraud score (0-100), carrier info, and abuse history.
                </p>
                <p className="text-xs text-green-700 mb-2">
                  <strong>Free tier:</strong> 1,000 lookups per month
                </p>
                <code className="text-xs bg-green-100 px-2 py-1 rounded block text-green-900">
                  IPQUALITYSCORE_ENABLED=true<br />
                  IPQUALITYSCORE_API_KEY=your_api_key<br />
                  IPQUALITYSCORE_FRAUD_SCORE_THRESHOLD=85
                </code>
                <a
                  href="https://www.ipqualityscore.com/create-account"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-green-700 hover:text-green-900 underline mt-2 inline-block"
                >
                  Get free API key →
                </a>
              </div>

              <div className="mt-4 p-4 bg-gray-50 rounded-md">
                <h4 className="font-medium mb-2">Twilio Integration (Alternative)</h4>
                <p className="text-sm text-gray-600 mb-2">
                  Twilio Lookup API provides real-time carrier type identification.
                  Use as fallback if IPQualityScore is not configured.
                </p>
                <p className="text-xs text-gray-500 mb-2">
                  <strong>Cost:</strong> ~$0.005 per lookup
                </p>
                <code className="text-xs bg-gray-200 px-2 py-1 rounded block">
                  TWILIO_ENABLED=true<br />
                  TWILIO_ACCOUNT_SID=your_sid<br />
                  TWILIO_AUTH_TOKEN=your_token
                </code>
              </div>

              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
                <h4 className="font-medium mb-2 text-blue-900">Detection Priority</h4>
                <ol className="text-sm text-blue-800 list-decimal list-inside space-y-1">
                  <li><strong>IPQualityScore</strong> - Most comprehensive (VoIP + fraud score)</li>
                  <li><strong>Twilio Lookup</strong> - Real-time carrier type (US only)</li>
                  <li><strong>Carrier Pattern Matching</strong> - Uses the patterns above</li>
                  <li><strong>VoIP Area Codes</strong> - US reserved area codes</li>
                </ol>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
