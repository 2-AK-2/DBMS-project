import React, { useState } from 'react';
import { Search, Plus, Menu, User, Clock, Tag, MapPin, Bell, Calendar, X, Image } from 'lucide-react';
export default function MemoryVault() {
  const [currentScreen, setCurrentScreen] = useState('login');
  const [role, setRole] = useState('patient');
  //const [selectedMemory, setSelectedMemory] = useState(null);
  
  //const memories = [
    //{ id: 1, title: 'Beach Vacation', date: '2024-06-15', tags: ['vacation', 'family'], place: 'Miami Beach' },
    //{ id: 2, title: 'Birthday Party', date: '2024-08-20', tags: ['celebration'], place: 'Home' },
    //{ id: 3, title: 'Graduation Day', date: '2024-05-10', tags: ['achievement'], place: 'University' },
 // ];

  const reminders = [
    { id: 1, text: 'Take morning medication', time: '8:00 AM' },
    { id: 2, text: 'Doctor appointment', time: '2:00 PM' },
    { id: 3, text: 'Evening walk', time: '6:00 PM' },
  ];

  const LoginScreen = () => (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-purple-600 to-indigo-600 rounded-2xl mb-4">
            <Image className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-800">Memory Vault</h1>
          <p className="text-gray-500 mt-2">Preserve your precious moments</p>
        </div>
        
        <div className="space-y-4 mb-6">
          <input
            type="email"
            placeholder="Email"
            className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:outline-none transition-colors"
          />
          <input
            type="password"
            placeholder="Password"
            className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:outline-none transition-colors"
          />
        </div>
        
        <button
          onClick={() => setCurrentScreen('home')}
          className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white py-3 rounded-xl font-semibold hover:from-purple-700 hover:to-indigo-700 transition-all shadow-lg hover:shadow-xl"
        >
          LOGIN
        </button>
        
        <button className="w-full text-purple-600 py-2 mt-4 hover:text-purple-700 transition-colors">
          Forgot Password?
        </button>
        
        <div className="mt-6 pt-6 border-t border-gray-200">
          <p className="text-sm text-gray-600 text-center mb-3">Role</p>
          <div className="flex justify-center gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="role"
                value="patient"
                checked={role === 'patient'}
                onChange={(e) => setRole(e.target.value)}
                className="w-4 h-4 text-purple-600"
              />
              <span className="text-gray-700">Patient</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="role"
                value="family"
                checked={role === 'family'}
                onChange={(e) => setRole(e.target.value)}
                className="w-4 h-4 text-purple-600"
              />
              <span className="text-gray-700">Family Caregiver</span>
            </label>
          </div>
        </div>
      </div>
    </div>
  );

  const HomeScreen = () => (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50">
      <div className="max-w-4xl mx-auto p-4">
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
          <div className="bg-gradient-to-r from-purple-600 to-indigo-600 p-6 flex items-center justify-between">
            <button className="text-white">
              <Menu className="w-6 h-6" />
            </button>
            <h1 className="text-2xl font-bold text-white">Memory Vault</h1>
            <button className="text-white">
              <User className="w-6 h-6" />
            </button>
          </div>
          
          <div className="p-6">
            <div className="grid grid-cols-2 gap-4 mb-6">
              <button
                onClick={() => setCurrentScreen('detail')}
                className="bg-gradient-to-br from-purple-500 to-purple-600 text-white p-6 rounded-xl hover:from-purple-600 hover:to-purple-700 transition-all shadow-lg hover:shadow-xl"
              >
                <Plus className="w-6 h-6 mx-auto mb-2" />
                <span className="font-semibold">Add Memory</span>
              </button>
              <button
                onClick={() => setCurrentScreen('search')}
                className="bg-gradient-to-br from-indigo-500 to-indigo-600 text-white p-6 rounded-xl hover:from-indigo-600 hover:to-indigo-700 transition-all shadow-lg hover:shadow-xl"
              >
                <Search className="w-6 h-6 mx-auto mb-2" />
                <span className="font-semibold">Search Memories</span>
              </button>
              <button className="bg-gradient-to-br from-blue-500 to-blue-600 text-white p-6 rounded-xl hover:from-blue-600 hover:to-blue-700 transition-all shadow-lg hover:shadow-xl">
                <Bell className="w-6 h-6 mx-auto mb-2" />
                <span className="font-semibold">Reminders</span>
              </button>
              <button className="bg-gradient-to-br from-pink-500 to-pink-600 text-white p-6 rounded-xl hover:from-pink-600 hover:to-pink-700 transition-all shadow-lg hover:shadow-xl">
                <User className="w-6 h-6 mx-auto mb-2" />
                <span className="font-semibold">Family Access</span>
              </button>
            </div>
            
            <div className="mt-8">
              <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
                <Bell className="w-5 h-5 text-purple-600" />
                Reminders
              </h2>
              <div className="grid grid-cols-2 gap-3">
                {reminders.map((reminder) => (
                  <div key={reminder.id} className="bg-gradient-to-br from-purple-100 to-indigo-100 p-4 rounded-xl border-2 border-purple-200">
                    <p className="font-medium text-gray-800 text-sm">{reminder.text}</p>
                    <p className="text-xs text-purple-600 mt-1">{reminder.time}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const SearchScreen = () => (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50">
      <div className="max-w-4xl mx-auto p-4">
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
          <div className="bg-gradient-to-r from-purple-600 to-indigo-600 p-6 flex items-center justify-between">
            <button onClick={() => setCurrentScreen('home')} className="text-white">
              <X className="w-6 h-6" />
            </button>
            <h1 className="text-2xl font-bold text-white">Search Memories</h1>
            <button className="text-white">
              <User className="w-6 h-6" />
            </button>
          </div>
          
          <div className="p-6">
            <div className="relative mb-6">
              <Search className="absolute left-4 top-3.5 text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder="Search by tag, year, place, or person"
                className="w-full pl-12 pr-4 py-3 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:outline-none"
              />
            </div>
            
            <div className="flex gap-3 mb-6">
              <button className="px-4 py-2 bg-purple-100 text-purple-700 rounded-lg font-medium hover:bg-purple-200 transition-colors flex items-center gap-2">
                <Clock className="w-4 h-4" />
                Time
              </button>
              <button className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition-colors flex items-center gap-2">
                <Tag className="w-4 h-4" />
                Tags
              </button>
              <button className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition-colors flex items-center gap-2">
                <User className="w-4 h-4" />
                People
              </button>
            </div>
            
            <input
              type="text"
              placeholder="Place"
              className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:outline-none mb-6"
            />
            
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">People in this memory</h3>
              <div className="flex gap-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="w-16 h-16 bg-gradient-to-br from-purple-200 to-indigo-200 rounded-xl flex items-center justify-center">
                    <User className="w-8 h-8 text-purple-600" />
                  </div>
                ))}
              </div>
            </div>
            
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Matching People</h3>
              <div className="bg-gradient-to-br from-purple-50 to-indigo-50 p-4 rounded-xl border-2 border-purple-200">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-purple-400 to-indigo-400 rounded-full flex items-center justify-center">
                    <User className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-800">Family Member</p>
                    <p className="text-sm text-gray-600">3 memories</p>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="mt-6">
              <h3 className="text-lg font-bold text-gray-800 mb-3">Annotations</h3>
              <div className="bg-yellow-50 p-4 rounded-xl border-2 border-yellow-200">
                <p className="text-sm text-gray-700">Notes and memories shared by family members will appear here.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const DetailScreen = () => (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50">
      <div className="max-w-4xl mx-auto p-4">
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
          <div className="bg-gradient-to-r from-purple-600 to-indigo-600 p-6 flex items-center justify-between">
            <button onClick={() => setCurrentScreen('home')} className="text-white">
              <X className="w-6 h-6" />
            </button>
            <h1 className="text-2xl font-bold text-white">Memory Detail</h1>
            <button className="text-white">
              <Plus className="w-6 h-6" />
            </button>
          </div>
          
          <div className="p-6">
            <div className="bg-gradient-to-br from-gray-100 to-gray-200 rounded-2xl h-64 flex items-center justify-center mb-6">
              <Image className="w-24 h-24 text-gray-400" />
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="text-sm font-semibold text-gray-700 mb-2 block">Title</label>
                <input
                  type="text"
                  placeholder="Give this memory a title"
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:outline-none"
                />
              </div>
              
              <div>
                <label className="text-sm font-semibold text-gray-700 mb-2 block">Description</label>
                <textarea
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
                  <input
                    type="date"
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:outline-none"
                  />
                </div>
                
                <div>
                  <label className="text-sm font-semibold text-gray-700 mb-2 block flex items-center gap-2">
                    <Tag className="w-4 h-4 text-purple-600" />
                    Tags
                  </label>
                  <input
                    type="text"
                    placeholder="vacation, family..."
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:outline-none"
                  />
                </div>
              </div>
              
              <div>
                <label className="text-sm font-semibold text-gray-700 mb-2 block flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-purple-600" />
                  Place
                </label>
                <input
                  type="text"
                  placeholder="Where was this?"
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:outline-none"
                />
              </div>
              
              <button className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white py-4 rounded-xl font-semibold hover:from-purple-700 hover:to-indigo-700 transition-all shadow-lg hover:shadow-xl flex items-center justify-center gap-2">
                <Bell className="w-5 h-5" />
                Set Reminder for this Memory
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
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
