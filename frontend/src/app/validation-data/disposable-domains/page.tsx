"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getDisposableDomains,
  getDisposableDomainsStatus,
  addDisposableDomain,
  removeDisposableDomain,
  syncDisposableDomains,
  type DisposableDomainsStatusResponse,
} from "@/lib/api";
import { Header } from "@/components/header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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

export default function DisposableDomainsPage() {
  const [domains, setDomains] = useState<string[]>([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState<DisposableDomainsStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newDomain, setNewDomain] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [page, setPage] = useState(0);
  const pageSize = 50;

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [domainsResponse, statusResponse] = await Promise.all([
        getDisposableDomains(pageSize, page * pageSize),
        getDisposableDomainsStatus(),
      ]);
      setDomains(domainsResponse.domains);
      setTotal(domainsResponse.total);
      setStatus(statusResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleAddDomain = async () => {
    if (!newDomain.trim()) return;

    try {
      await addDisposableDomain(newDomain.trim());
      setNewDomain("");
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add domain");
    }
  };

  const handleRemoveDomain = async (domain: string) => {
    try {
      await removeDisposableDomain(domain);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove domain");
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setError(null);
    try {
      await syncDisposableDomains();
      // Poll for completion
      const pollInterval = setInterval(async () => {
        const statusResponse = await getDisposableDomainsStatus();
        setStatus(statusResponse);
        if (statusResponse.last_sync) {
          clearInterval(pollInterval);
          setSyncing(false);
          loadData();
        }
      }, 2000);

      // Timeout after 60 seconds
      setTimeout(() => {
        clearInterval(pollInterval);
        setSyncing(false);
      }, 60000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start sync");
      setSyncing(false);
    }
  };

  const filteredDomains = searchTerm
    ? domains.filter((d) => d.includes(searchTerm.toLowerCase()))
    : domains;

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <div className="container mx-auto py-8 px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Disposable Email Domains</h1>
          <p className="text-gray-600 mt-2">
            Manage the list of known disposable email providers.
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
              <CardTitle className="text-lg">Total Domains</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-blue-600">
                {status?.domain_count.toLocaleString() || "..."}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">Last Synced</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-sm">
                {status?.last_sync ? (
                  <>
                    <div className="font-medium">
                      {new Date(status.last_sync.completed_at).toLocaleDateString()}
                    </div>
                    <div className="text-gray-500">
                      {status.last_sync.source_name}
                    </div>
                  </>
                ) : (
                  <span className="text-gray-500">Never synced</span>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <Button
                onClick={handleSync}
                disabled={syncing}
                className="w-full"
              >
                {syncing ? "Syncing..." : "Sync from GitHub"}
              </Button>
            </CardContent>
          </Card>
        </div>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Add Custom Domain</CardTitle>
            <CardDescription>
              Add a domain that isn&apos;t in the external list
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Input
                placeholder="example-disposable.com"
                value={newDomain}
                onChange={(e) => setNewDomain(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAddDomain()}
                className="max-w-md"
              />
              <Button onClick={handleAddDomain} disabled={!newDomain.trim()}>
                Add Domain
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Domain List</CardTitle>
            <CardDescription>
              Search and manage disposable email domains
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="mb-4">
              <Input
                placeholder="Search domains..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="max-w-md"
              />
            </div>

            {loading ? (
              <div className="text-center py-8 text-gray-500">Loading...</div>
            ) : (
              <>
                <div className="border rounded-md">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Domain</TableHead>
                        <TableHead className="w-24">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredDomains.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={2} className="text-center text-gray-500">
                            {searchTerm ? "No matching domains" : "No domains loaded"}
                          </TableCell>
                        </TableRow>
                      ) : (
                        filteredDomains.map((domain) => (
                          <TableRow key={domain}>
                            <TableCell className="font-mono text-sm">{domain}</TableCell>
                            <TableCell>
                              <Button
                                variant="outline"
                                size="sm"
                                className="text-red-600 hover:text-red-700"
                                onClick={() => handleRemoveDomain(domain)}
                              >
                                Remove
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>

                {totalPages > 1 && (
                  <div className="mt-4 flex items-center justify-between">
                    <p className="text-sm text-gray-600">
                      Showing {page * pageSize + 1}-{Math.min((page + 1) * pageSize, total)} of{" "}
                      {total.toLocaleString()} domains
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage((p) => Math.max(0, p - 1))}
                        disabled={page === 0}
                      >
                        Previous
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                        disabled={page >= totalPages - 1}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
