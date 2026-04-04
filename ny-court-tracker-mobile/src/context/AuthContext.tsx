import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { storage } from "../services/storage";
import { authApi, User } from "../services/api";

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (token: string, user: User) => Promise<void>;
  logout: () => Promise<void>;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  login: async () => {},
  logout: async () => {},
  loading: true,
});

export const useAuth = () => useContext(AuthContext);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadAuth = async () => {
      try {
        const storedToken = await storage.getItem("token");
        const storedUser = await storage.getItem("user");
        if (storedToken && storedUser) {
          setToken(storedToken);
          setUser(JSON.parse(storedUser));
          // Verify token is still valid
          try {
            const res = await authApi.me();
            setUser(res.data);
          } catch {
            await storage.deleteItem("token");
            await storage.deleteItem("user");
            setToken(null);
            setUser(null);
          }
        }
      } catch {
        // Ignore errors
      } finally {
        setLoading(false);
      }
    };
    loadAuth();
  }, []);

  const login = useCallback(async (newToken: string, newUser: User) => {
    await storage.setItem("token", newToken);
    await storage.setItem("user", JSON.stringify(newUser));
    setToken(newToken);
    setUser(newUser);
  }, []);

  const logout = useCallback(async () => {
    await storage.deleteItem("token");
    await storage.deleteItem("user");
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};
