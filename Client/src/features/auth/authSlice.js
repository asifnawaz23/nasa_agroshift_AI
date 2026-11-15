import { createSlice } from '@reduxjs/toolkit';

// Optional: check localStorage so the user stays logged in on page refresh
const initialUser = localStorage.getItem('user') 
  ? JSON.parse(localStorage.getItem('user')) 
  : null;

const initialToken = localStorage.getItem('token') || null;

const initialState = {
  user: initialUser,
  token: initialToken,
  isAuthenticated: !!initialToken,
  isLoading: false,
  error: null,
};

export const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    // Call this when login starts (if handling async requests)
    authStart: (state) => {
      state.isLoading = true;
      state.error = null;
    },
    // Call this when login succeeds
    loginSuccess: (state, action) => {
      state.isLoading = false;
      state.isAuthenticated = true;
      state.user = action.payload.user;
      state.token = action.payload.token;
      state.error = null;

      // Save to localStorage for persistence
      localStorage.setItem('user', JSON.stringify(action.payload.user));
      localStorage.setItem('token', action.payload.token);
    },
    // Call this when the user's details change (e.g. new profile picture)
    updateUser: (state, action) => {
      state.user = { ...state.user, ...action.payload };
      localStorage.setItem('user', JSON.stringify(state.user));
    },
    // Call this if login fails
    authFailure: (state, action) => {
      state.isLoading = false;
      state.error = action.payload;
    },
    // Call this to log out
    logout: (state) => {
      state.user = null;
      state.token = null;
      state.isAuthenticated = false;
      state.isLoading = false;
      state.error = null;

      // Clear localStorage
      localStorage.removeItem('user');
      localStorage.removeItem('token');
    },
  },
});

// Export the generated actions
export const { authStart, loginSuccess, updateUser, authFailure, logout } = authSlice.actions;

// Export the reducer to add to your store
export default authSlice.reducer;