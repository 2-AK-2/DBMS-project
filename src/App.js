// src/App.js
import React, { useState, useEffect } from 'react';
import { Search, Plus, Menu, User, Clock, Tag, MapPin, Bell, Calendar, X, Image } from 'lucide-react';

const API_BASE_URL = 'http://localhost:5000'; // Our Python backend

export default function MemoryVault() {
  const [currentScreen, setCurrentScreen] = useState('login');
  const [role, setRole] = useState('patient');
  
  // State for data fetched from the backend
  const [memories, setMemories] = useState([]);
  const [reminders, setReminders] = useState([]);

  // --- Data Fetching ---
  useEffect(() => {
    // This effect runs when the component mounts
    // Fetch initial data if logged in
    if (currentScreen === 'home') {
      fetchMemories();
      // You would also fetch reminders here if you had an endpoint
      // For now, we'll keep the static reminders
      setReminders([
        { id: 1, text: 'Take morning medication', time: '8:00 AM' },
        { id: 2, text: 'Doctor appointment', time: '2:00 PM' },
        { id: 3, text: 'Evening walk', time: '6:00 PM' },
      ]);
    }
  }, [currentScreen]);

  const fetchMemories = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/memories`);
      const data = await response.json();
      setMemories(data);
    } catch (error) {
      console.error("Error fetching memories:", error);
    }
  };

  // --- Event Handlers ---
  const handleLogin = async () => {
    // In a real app, you'd get the email/password from state
    try {
      const response = await fetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'test@test.com', password: 'password' }),
      });

      if (response.ok) {
        setCurrentScreen('home');
      } else {
        alert('Login failed!');
      }
    } catch (error) {
      console.error("Login error:", error);
    }
  };

  const handleAddMemory = async (event) => {
    event.preventDefault();
    const formData = new FormData(event.target);
    
    try {
      const response = await fetch(`${API_BASE_URL}/memories`, {
        method: 'POST',
        body: formData, // FormData handles the multipart/form-data for file uploads
      });

      if (response.ok) {
        alert('Memory added successfully!');
        setCurrentScreen('home'); // Go back home after adding
      } else {
        alert('Failed to add memory.');
      }
    } catch (error) {
      console.error("Error adding memory:", error);
    }
  };


  // --- COMPONENTS (Screens) ---

  const LoginScreen = () => (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
        {/* ... (Login form UI is the same) ... */}
        <button
          onClick={handleLogin} // Use the handler function
          className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white py-3 rounded-xl font-semibold hover:from-purple-700 hover:to-indigo-700 transition-all shadow-lg hover:shadow-xl"
        >
          LOGIN
        </button>
        {/* ... (Rest of the login UI) ... */}
      </div>
    </div>
  );
  
  // HomeScreen now displays dynamic memories
  const HomeScreen = () => (
     <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50">
        <div className="max-w-4xl mx-auto p-4">
          <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
             {/* ... (Header UI is the same) ... */}
             <div className="p-6">
                {/* ... (Buttons are the same) ... */}

                {/* --- Display Memories --- */}
                <div className="mt-8">
                  <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
                    <Image className="w-5 h-5 text-indigo-600" />
                    Recent Memories
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {memories.map((memory) => (
                      <div key={memory.id} className="bg-gray-50 p-4 rounded-lg border">
                        <p className="font-bold text-gray-800">{memory.title}</p>
                        <p className="text-sm text-gray-500">{new Date(memory.date).toLocaleDateString()}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* ... (Reminders section is the same) ... */}
             </div>
          </div>
        </div>
     </div>
  );

  // DetailScreen now has a form that submits data
  const DetailScreen = () => (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50">
      <div className="max-w-4xl mx-auto p-4">
        {/* onSubmit is added to the form */}
        <form className="bg-white rounded-2xl shadow-xl overflow-hidden" onSubmit={handleAddMemory}>
          <div className="bg-gradient-to-r from-purple-600 to-indigo-600 p-6 flex items-center justify-between">
            <button type="button" onClick={() => setCurrentScreen('home')} className="text-white">
              <X className="w-6 h-6" />
            </button>
            <h1 className="text-2xl font-bold text-white">Add a New Memory</h1>
            <button type="submit" className="text-white">
              <Plus className="w-6 h-6" />
            </button>
          </div>
          
          <div className="p-6">
            <div className="bg-gradient-to-br from-gray-100 to-gray-200 rounded-2xl h-64 flex items-center justify-center mb-6">
              {/* Add name="image" to the file input */}
              <input type="file" name="image" required />
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="text-sm font-semibold text-gray-700 mb-2 block">Title</label>
                {/* Add name="title" to the input */}
                <input
                  type="text"
                  name="title"
                  placeholder="Give this memory a title"
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:outline-none"
                  required
                />
              </div>
              
              <div>
                <label className="text-sm font-semibold text-gray-700 mb-2 block">Description</label>
                {/* Add name="description" to the textarea */}
                <textarea
                  name="description"
                  placeholder="Describe this memory..."
                  rows="3"
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:outline-none resize-none"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-semibold text-gray-700 mb-2 block flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-purple-600" />
                    Date
                  </label>
                  {/* Add name="date" to the input */}
                  <input
                    type="date"
                    name="date"
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:outline-none"
                    required
                  />
                </div>
                {/* ... (Tags and Place inputs) ... */}
              </div>
              <button type="submit" className="w-full bg-gradient-to-r from-green-500 to-emerald-600 text-white py-4 rounded-xl font-semibold">
                Save Memory
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );

  // The SearchScreen component remains the same for now
  const SearchScreen = () => (
      // ... (your existing search UI) ...
      <></>
  );

  return (
    <>
      {currentScreen === 'login' && <LoginScreen />}
      {currentScreen === 'home' && <HomeScreen />}
      {currentScreen === 'search' && <SearchScreen />}
      {currentScreen === 'detail' && <DetailScreen />}
    </>
  );
}