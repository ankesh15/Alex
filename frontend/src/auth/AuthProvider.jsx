import React, { createContext, useContext, useEffect, useState } from 'react';
import { fetchCurrentUser, signIn, signUp, signOut, clearAuthSession } from '../services/api';

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const restore = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCurrentUser();
      setUser(data.user);
    } catch (err) {
      setUser(null);
      if (err.status !== 401) setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    const expired = () => { clearAuthSession(); setUser(null); setError(null); };
    window.addEventListener('alex:unauthorized', expired);
    const bootstrap = async () => {
      try {
        const data = await fetchCurrentUser();
        if (active) setUser(data.user);
      } catch (err) {
        if (active && err.status !== 401) setError(err.message);
      } finally {
        if (active) setLoading(false);
      }
    };
    bootstrap();
    return () => { active = false; window.removeEventListener('alex:unauthorized', expired); };
  }, []);

  const authenticate = async (mode, email, password) => {
    const data = await (mode === 'signup' ? signUp : signIn)(email, password);
    setUser(data.user);
    setError(null);
  };
  const logout = async () => {
    await signOut();
    setUser(null);
  };

  return <AuthContext.Provider value={{ user, loading, error, restore, authenticate, logout }}>{children}</AuthContext.Provider>;
}
