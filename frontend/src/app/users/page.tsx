"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth-context";
import { Header } from "@/components/header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  must_change_password: boolean;
  last_login_at: string | null;
  created_at: string;
}

interface CreateUserResponse {
  id: string;
  email: string;
  name: string;
  role: string;
  temp_password: string;
}

const ROLES = [
  { value: "viewer", label: "Viewer", description: "Read-only access" },
  { value: "user", label: "User", description: "View + edit applicants" },
  { value: "admin", label: "Admin", description: "Full access + manage users" },
  { value: "superadmin", label: "Super Admin", description: "Full access + manage admins" },
];

function getRoleBadgeColor(role: string): string {
  switch (role) {
    case "superadmin":
      return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200";
    case "admin":
      return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
    case "user":
      return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
    case "viewer":
      return "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

export default function UsersPage() {
  const { isAdmin, isSuperAdmin, loading: authLoading } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create user form state
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState("");
  const [newUserName, setNewUserName] = useState("");
  const [newUserRole, setNewUserRole] = useState("user");
  const [creating, setCreating] = useState(false);
  const [createdUser, setCreatedUser] = useState<CreateUserResponse | null>(null);

  // Reset password dialog
  const [resetPasswordUser, setResetPasswordUser] = useState<User | null>(null);
  const [resetTempPassword, setResetTempPassword] = useState<string | null>(null);

  // Deactivate dialog
  const [deactivateUser, setDeactivateUser] = useState<User | null>(null);

  const loadUsers = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/users`, {
        credentials: "include",
      });

      if (response.ok) {
        const data = await response.json();
        setUsers(data);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || "Failed to load users");
      }
    } catch (err) {
      setError("Failed to load users");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!authLoading && isAdmin) {
      loadUsers();
    }
  }, [authLoading, isAdmin, loadUsers]);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/api/users`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({
          email: newUserEmail,
          name: newUserName,
          role: newUserRole,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setCreatedUser(data);
        setShowCreateForm(false);
        setNewUserEmail("");
        setNewUserName("");
        setNewUserRole("user");
        loadUsers();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || "Failed to create user");
      }
    } catch (err) {
      setError("Failed to create user");
    } finally {
      setCreating(false);
    }
  };

  const handleResetPassword = async () => {
    if (!resetPasswordUser) return;

    try {
      const response = await fetch(
        `${API_BASE}/api/users/${resetPasswordUser.id}/reset-password`,
        {
          method: "POST",
          credentials: "include",
        }
      );

      if (response.ok) {
        const data = await response.json();
        setResetTempPassword(data.temp_password);
        loadUsers();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || "Failed to reset password");
      }
    } catch (err) {
      setError("Failed to reset password");
    }
  };

  const handleDeactivate = async () => {
    if (!deactivateUser) return;

    try {
      const response = await fetch(`${API_BASE}/api/users/${deactivateUser.id}`, {
        method: "DELETE",
        credentials: "include",
      });

      if (response.ok) {
        setDeactivateUser(null);
        loadUsers();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || "Failed to deactivate user");
      }
    } catch (err) {
      setError("Failed to deactivate user");
    }
  };

  const handleToggleActive = async (user: User) => {
    try {
      const response = await fetch(`${API_BASE}/api/users/${user.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({
          is_active: !user.is_active,
        }),
      });

      if (response.ok) {
        loadUsers();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || "Failed to update user");
      }
    } catch (err) {
      setError("Failed to update user");
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <Header />
        <main className="container mx-auto px-4 py-8">
          <div className="flex items-center justify-center h-64">
            <p className="text-gray-500">Loading...</p>
          </div>
        </main>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <Header />
        <main className="container mx-auto px-4 py-8">
          <div className="flex items-center justify-center h-64">
            <p className="text-red-500">Access denied. Admin privileges required.</p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Header />
      <main className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">User Management</h1>
          <Button onClick={() => setShowCreateForm(true)}>
            Create User
          </Button>
        </div>

        {error && (
          <div className="mb-4 p-3 text-sm text-red-500 bg-red-50 dark:bg-red-900/20 rounded-md border border-red-200 dark:border-red-800">
            {error}
            <button
              onClick={() => setError(null)}
              className="ml-2 text-red-700 hover:text-red-900"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Create User Form */}
        {showCreateForm && (
          <div className="mb-6 p-4 bg-white dark:bg-gray-800 rounded-lg border">
            <h2 className="text-lg font-semibold mb-4">Create New User</h2>
            <form onSubmit={handleCreateUser} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="newEmail">Email</Label>
                  <Input
                    id="newEmail"
                    type="email"
                    value={newUserEmail}
                    onChange={(e) => setNewUserEmail(e.target.value)}
                    required
                    placeholder="user@company.com"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="newName">Name</Label>
                  <Input
                    id="newName"
                    type="text"
                    value={newUserName}
                    onChange={(e) => setNewUserName(e.target.value)}
                    required
                    placeholder="Full Name"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="newRole">Role</Label>
                  <Select value={newUserRole} onValueChange={setNewUserRole}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ROLES.map((role) => (
                        <SelectItem
                          key={role.value}
                          value={role.value}
                          disabled={role.value === "superadmin" && !isSuperAdmin}
                        >
                          {role.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex gap-2">
                <Button type="submit" disabled={creating}>
                  {creating ? "Creating..." : "Create User"}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowCreateForm(false)}
                >
                  Cancel
                </Button>
              </div>
            </form>
          </div>
        )}

        {/* Users Table */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Login</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell className="font-medium">{user.name}</TableCell>
                  <TableCell>{user.email}</TableCell>
                  <TableCell>
                    <Badge className={getRoleBadgeColor(user.role)}>
                      {user.role}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge
                      className={
                        user.is_active
                          ? "bg-green-100 text-green-800"
                          : "bg-red-100 text-red-800"
                      }
                    >
                      {user.is_active ? "Active" : "Inactive"}
                    </Badge>
                    {user.must_change_password && (
                      <Badge className="ml-1 bg-yellow-100 text-yellow-800">
                        Password Reset
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-gray-500">
                    {user.last_login_at
                      ? new Date(user.last_login_at).toLocaleDateString()
                      : "Never"}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setResetPasswordUser(user)}
                        disabled={user.role === "superadmin" && !isSuperAdmin}
                      >
                        Reset Password
                      </Button>
                      {user.is_active ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDeactivateUser(user)}
                          disabled={user.role === "superadmin" && !isSuperAdmin}
                        >
                          Deactivate
                        </Button>
                      ) : (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleToggleActive(user)}
                        >
                          Reactivate
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Created User Dialog */}
        <AlertDialog
          open={!!createdUser}
          onOpenChange={() => setCreatedUser(null)}
        >
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>User Created Successfully</AlertDialogTitle>
              <AlertDialogDescription className="space-y-2">
                <p>
                  <strong>{createdUser?.name}</strong> ({createdUser?.email}) has
                  been created.
                </p>
                <p>Temporary password:</p>
                <code className="block p-2 bg-gray-100 dark:bg-gray-800 rounded font-mono text-sm">
                  {createdUser?.temp_password}
                </code>
                <p className="text-yellow-600 dark:text-yellow-400">
                  Please share this password securely. The user will be required
                  to change it on first login.
                </p>
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogAction onClick={() => setCreatedUser(null)}>
                Done
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        {/* Reset Password Dialog */}
        <AlertDialog
          open={!!resetPasswordUser && !resetTempPassword}
          onOpenChange={() => setResetPasswordUser(null)}
        >
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Reset Password</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to reset the password for{" "}
                <strong>{resetPasswordUser?.name}</strong>? They will receive a
                new temporary password.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel onClick={() => setResetPasswordUser(null)}>
                Cancel
              </AlertDialogCancel>
              <AlertDialogAction onClick={handleResetPassword}>
                Reset Password
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        {/* Reset Password Result Dialog */}
        <AlertDialog
          open={!!resetTempPassword}
          onOpenChange={() => {
            setResetTempPassword(null);
            setResetPasswordUser(null);
          }}
        >
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Password Reset</AlertDialogTitle>
              <AlertDialogDescription className="space-y-2">
                <p>
                  Password for <strong>{resetPasswordUser?.name}</strong> has been
                  reset.
                </p>
                <p>New temporary password:</p>
                <code className="block p-2 bg-gray-100 dark:bg-gray-800 rounded font-mono text-sm">
                  {resetTempPassword}
                </code>
                <p className="text-yellow-600 dark:text-yellow-400">
                  Please share this password securely. The user will be required
                  to change it on next login.
                </p>
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogAction
                onClick={() => {
                  setResetTempPassword(null);
                  setResetPasswordUser(null);
                }}
              >
                Done
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        {/* Deactivate Dialog */}
        <AlertDialog
          open={!!deactivateUser}
          onOpenChange={() => setDeactivateUser(null)}
        >
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Deactivate User</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to deactivate{" "}
                <strong>{deactivateUser?.name}</strong>? They will no longer be
                able to log in.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel onClick={() => setDeactivateUser(null)}>
                Cancel
              </AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDeactivate}
                className="bg-red-600 hover:bg-red-700"
              >
                Deactivate
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </main>
    </div>
  );
}
