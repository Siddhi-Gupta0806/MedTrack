import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  MapPin, 
  Search, 
  Calendar, 
  MessageSquare, 
  AlertTriangle, 
  RefreshCw, 
  Shuffle, 
  User, 
  CheckCircle, 
  AlertCircle, 
  ArrowRight,
  Database,
  BriefcaseMedical,
  FileText
} from 'lucide-react';

const API_BASE = "http://localhost:8000/api";

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [hospitals, setHospitals] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [transfers, setTransfers] = useState([]);
  const [redirects, setRedirects] = useState([]);
  const [outbreakStatus, setOutbreakStatus] = useState({});
  const [simulationLogs, setSimulationLogs] = useState([]);
  const [isSimulating, setIsSimulating] = useState(false);
  const [loading, setLoading] = useState(true);

  // Chatbot state
  const [chatHistory, setChatHistory] = useState([
    { role: 'model', text: "**Welcome to MedTrack AI Triage.** Describe your symptoms, and I will recommend a clinic specialty and urgency level.\n\n*DISCLAIMER: I am a chatbot and do not provide medical diagnosis. Go to the ER for emergencies.*" }
  ]);
  const [chatMessage, setChatMessage] = useState('');
  const [triageSuggestion, setTriageSuggestion] = useState(null);

  // Booking form state
  const [patientName, setPatientName] = useState('');
  const [selectedDoctorId, setSelectedDoctorId] = useState('');
  const [selectedSlot, setSelectedSlot] = useState('');
  const [bookingMessage, setBookingMessage] = useState(null);

  // Finder form state
  const [finderSpecialty, setFinderSpecialty] = useState('');
  const [finderX, setFinderX] = useState('15');
  const [finderY, setFinderY] = useState('20');
  const [finderMinBeds, setFinderMinBeds] = useState(0);
  const [finderMinIcu, setFinderMinIcu] = useState(0);
  const [finderMinVents, setFinderMinVents] = useState(0);
  const [finderResults, setFinderResults] = useState([]);

  // Fetch initial data
  const fetchData = async () => {
    try {
      const [hospRes, docRes, bookRes, transRes, redirRes, outRes] = await Promise.all([
        fetch(`${API_BASE}/hospitals`),
        fetch(`${API_BASE}/doctors`),
        fetch(`${API_BASE}/bookings`),
        fetch(`${API_BASE}/transfers`),
        fetch(`${API_BASE}/redirects`),
        fetch(`${API_BASE}/outbreak/status`)
      ]);

      const hospData = await hospRes.json();
      const docData = await docRes.json();
      const bookData = await bookRes.json();
      const transData = await transRes.json();
      const redirData = await redirRes.json();
      const outData = await outRes.json();

      setHospitals(hospData);
      setDoctors(docData);
      setBookings(bookData);
      setTransfers(transData);
      setRedirects(redirData);
      setOutbreakStatus(outData);
    } catch (error) {
      console.error("Failed to fetch MedTrack data:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Trigger search
  const handleFinderSearch = async (e) => {
    if (e) e.preventDefault();
    try {
      let url = `${API_BASE}/hospitals?`;
      if (finderSpecialty) url += `specialty=${encodeURIComponent(finderSpecialty)}&`;
      if (finderX) url += `x=${finderX}&`;
      if (finderY) url += `y=${finderY}&`;
      if (finderMinBeds > 0) url += `min_beds=${finderMinBeds}&`;
      if (finderMinIcu > 0) url += `min_icu=${finderMinIcu}&`;
      if (finderMinVents > 0) url += `min_ventilators=${finderMinVents}&`;

      const res = await fetch(url);
      const data = await res.json();
      setFinderResults(data);
    } catch (error) {
      console.error("Finder search failed:", error);
    }
  };

  // Run initial finder search on load
  useEffect(() => {
    if (activeTab === 'finder') {
      handleFinderSearch();
    }
  }, [activeTab]);

  // Simulate outbreak
  const handleSimulateOutbreak = async () => {
    setIsSimulating(true);
    setSimulationLogs([]);
    try {
      const res = await fetch(`${API_BASE}/simulation/run`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        // Stream logs with micro-delays for premium visual effect
        let index = 0;
        const interval = setInterval(() => {
          if (index < data.logs.length) {
            setSimulationLogs(prev => [...prev, data.logs[index]]);
            index++;
          } else {
            clearInterval(interval);
            setIsSimulating(false);
            fetchData(); // Refresh all DB states
          }
        }, 800);
      } else {
        setSimulationLogs(data.logs || [{ step: "ERROR", message: "Simulation failed." }]);
        setIsSimulating(false);
      }
    } catch (error) {
      console.error("Simulation failed:", error);
      setIsSimulating(false);
    }
  };

  // Reset simulation
  const handleResetSimulation = async () => {
    try {
      const res = await fetch(`${API_BASE}/simulation/reset`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        setSimulationLogs([]);
        fetchData();
        alert("Simulation states reset successfully.");
      }
    } catch (error) {
      console.error("Reset failed:", error);
    }
  };

  // Book appointment
  const handleBookAppointment = async (e) => {
    e.preventDefault();
    if (!patientName || !selectedDoctorId || !selectedSlot) {
      alert("Please fill in all booking fields.");
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/book`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_name: patientName,
          doctor_id: parseInt(selectedDoctorId),
          time_slot: selectedSlot
        })
      });

      const data = await res.json();
      if (res.ok) {
        setBookingMessage({
          success: true,
          message: data.message,
          details: data
        });
        // Clear fields
        setPatientName('');
        setSelectedDoctorId('');
        setSelectedSlot('');
        fetchData(); // Refresh slots & bookings
      } else {
        setBookingMessage({
          success: false,
          message: data.detail || "Booking failed."
        });
      }
    } catch (error) {
      console.error("Booking error:", error);
      setBookingMessage({
        success: false,
        message: "Network error occurred."
      });
    }
  };

  // Chat message submission
  const handleSendChatMessage = async (e) => {
    e.preventDefault();
    if (!chatMessage.trim()) return;

    const userMsg = { role: 'user', text: chatMessage };
    setChatHistory(prev => [...prev, userMsg]);
    const promptText = chatMessage;
    setChatMessage('');

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: promptText,
          history: chatHistory
        })
      });

      const data = await res.json();
      setChatHistory(prev => [...prev, { role: 'model', text: data.response }]);
      
      if (data.triage_level) {
        setTriageSuggestion({
          level: data.triage_level,
          specialty: data.specialty
        });
      }
    } catch (error) {
      console.error("Chat error:", error);
      setChatHistory(prev => [...prev, { role: 'model', text: "Error connecting to server. Please try again." }]);
    }
  };

  const getDoctorSlots = () => {
    if (!selectedDoctorId) return [];
    const doc = doctors.find(d => d.id === parseInt(selectedDoctorId));
    return doc ? doc.slots : [];
  };

  const getActiveRedirect = (hospitalId) => {
    return redirects.find(r => r.source_hospital === hospitals.find(h => h.id === hospitalId)?.name);
  };

  return (
    <div className="flex h-screen bg-[#0f172a] text-[#f1f5f9] overflow-hidden font-sans">
      
      {/* Sidebar Layout */}
      <aside className="w-72 bg-[#1e293b] border-r border-[#334155] flex flex-col justify-between shrink-0">
        <div>
          <div className="p-6 flex items-center space-x-3 border-b border-[#334155]">
            <Activity className="h-8 w-8 text-indigo-400 animate-pulse" />
            <div>
              <h1 className="text-xl font-bold text-white tracking-wide">MedTrack</h1>
              <p className="text-xs text-slate-400">Resource Control Center</p>
            </div>
          </div>
          
          <nav className="p-4 space-y-2">
            <button 
              onClick={() => setActiveTab('dashboard')} 
              className={`flex items-center space-x-3 w-full p-3 rounded-lg text-sm font-medium transition duration-200 ${activeTab === 'dashboard' ? 'bg-indigo-600 text-white shadow-lg' : 'hover:bg-slate-700 text-slate-300'}`}
            >
              <Activity className="h-5 w-5" />
              <span>Orchestrator & Status</span>
            </button>
            <button 
              onClick={() => setActiveTab('finder')} 
              className={`flex items-center space-x-3 w-full p-3 rounded-lg text-sm font-medium transition duration-200 ${activeTab === 'finder' ? 'bg-indigo-600 text-white shadow-lg' : 'hover:bg-slate-700 text-slate-300'}`}
            >
              <Search className="h-5 w-5" />
              <span>Hospital Finder</span>
            </button>
            <button 
              onClick={() => setActiveTab('triage')} 
              className={`flex items-center space-x-3 w-full p-3 rounded-lg text-sm font-medium transition duration-200 ${activeTab === 'triage' ? 'bg-indigo-600 text-white shadow-lg' : 'hover:bg-slate-700 text-slate-300'}`}
            >
              <MessageSquare className="h-5 w-5" />
              <span>Triage Chatbot</span>
            </button>
            <button 
              onClick={() => setActiveTab('bookings')} 
              className={`flex items-center space-x-3 w-full p-3 rounded-lg text-sm font-medium transition duration-200 ${activeTab === 'bookings' ? 'bg-indigo-600 text-white shadow-lg' : 'hover:bg-slate-700 text-slate-300'}`}
            >
              <Calendar className="h-5 w-5" />
              <span>Bookings & Redirects</span>
            </button>
          </nav>
        </div>

        <div className="p-6 border-t border-[#334155] bg-slate-900/40">
          <div className="flex items-center space-x-2 text-xs text-indigo-300 font-semibold mb-2 uppercase tracking-wider">
            <Database className="h-4 w-4" />
            <span>Mock Database Status</span>
          </div>
          <p className="text-xs text-slate-400">SQLite Connected: 9 Hospitals seeded across 3 Zones (A, B, C)</p>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <header className="h-16 border-b border-[#334155] bg-[#1e293b]/50 backdrop-blur-md flex items-center justify-between px-8 sticky top-0 z-40">
          <div className="flex items-center space-x-3">
            <span className="text-slate-400 capitalize text-sm">Navigation</span>
            <ArrowRight className="h-4 w-4 text-slate-500" />
            <span className="text-white font-semibold capitalize tracking-wide">{activeTab.replace('_', ' ')}</span>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 text-xs bg-slate-800 px-3 py-1.5 rounded-full border border-slate-700">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 animate-ping"></span>
              <span className="text-slate-300">Live Agent Orchestration</span>
            </div>
          </div>
        </header>

        <div className="p-8 max-w-7xl w-full mx-auto space-y-8 flex-1">
          
          {loading ? (
            <div className="flex flex-col items-center justify-center h-96 space-y-4">
              <RefreshCw className="h-12 w-12 text-indigo-500 animate-spin" />
              <p className="text-slate-400 font-medium">Loading MedTrack Systems...</p>
            </div>
          ) : (
            <>
              {/* TAB 1: DASHBOARD & LIVE ORCHESTRATOR */}
              {activeTab === 'dashboard' && (
                <div className="space-y-8">
                  {/* Simulation Controls Block */}
                  <div className="bg-gradient-to-r from-slate-800 to-indigo-950 p-6 rounded-2xl border border-indigo-500/30 shadow-2xl flex flex-col md:flex-row items-center justify-between gap-6">
                    <div className="space-y-2">
                      <div className="flex items-center space-x-2">
                        <BriefcaseMedical className="h-6 w-6 text-indigo-400" />
                        <h2 className="text-2xl font-bold text-white">Outbreak Mitigation Simulation</h2>
                      </div>
                      <p className="text-slate-300 text-sm max-w-2xl">
                        Simulate a case surge in **Zone A** to trigger the multi-agent loop: Outbreak flags zone → Equipment transfers ventilators/beds → Booking Agent auto-redirects new admissions.
                      </p>
                    </div>
                    <div className="flex items-center space-x-3 shrink-0">
                      <button 
                        onClick={handleSimulateOutbreak} 
                        disabled={isSimulating}
                        className={`px-6 py-3 rounded-xl font-bold text-sm tracking-wide shadow-md flex items-center space-x-2 transition duration-200 ${isSimulating ? 'bg-indigo-800/40 text-slate-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-500 text-white hover:scale-105 active:scale-95'}`}
                      >
                        {isSimulating ? <RefreshCw className="h-5 w-5 animate-spin" /> : <Shuffle className="h-5 w-5" />}
                        <span>{isSimulating ? "Simulating..." : "Simulate Outbreak"}</span>
                      </button>
                      <button 
                        onClick={handleResetSimulation}
                        className="px-5 py-3 rounded-xl border border-slate-600 bg-slate-800/50 hover:bg-slate-700/60 font-semibold text-sm text-slate-300 transition duration-200"
                      >
                        Reset Demo
                      </button>
                    </div>
                  </div>

                  {/* Outbreak Status Cards Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {Object.keys(outbreakStatus).map(zone => {
                      const status = outbreakStatus[zone];
                      const isAtRisk = status.is_at_risk;
                      return (
                        <div key={zone} className={`p-6 rounded-2xl border bg-slate-800/60 backdrop-blur-md transition duration-300 ${isAtRisk ? 'border-rose-500/50 shadow-lg shadow-rose-950/20' : 'border-slate-700/50'}`}>
                          <div className="flex items-center justify-between mb-4">
                            <span className="text-slate-400 font-bold uppercase tracking-wider text-xs">{zone}</span>
                            <span className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${isAtRisk ? 'bg-rose-500/20 text-rose-300 animate-pulse' : 'bg-emerald-500/20 text-emerald-300'}`}>
                              {isAtRisk ? "At Risk" : "Stable"}
                            </span>
                          </div>
                          <div className="space-y-1">
                            <div className="text-3xl font-black text-white">{status.latest_count} cases</div>
                            <div className="text-xs text-slate-400">Previous Case Average: {status.previous_count}</div>
                          </div>
                          <div className="mt-4 pt-4 border-t border-slate-700/60 flex items-center justify-between text-xs">
                            <span className="text-slate-500">Case Growth Rate</span>
                            <span className={`font-bold ${status.growth_rate > 0.20 ? 'text-rose-400' : 'text-emerald-400'}`}>
                              {(status.growth_rate * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Simulation Execution Log (if any active) */}
                  {simulationLogs.length > 0 && (
                    <div className="bg-[#1e293b] p-6 rounded-2xl border border-slate-700/80 shadow-lg space-y-4">
                      <div className="flex items-center justify-between border-b border-slate-700 pb-3">
                        <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                          <FileText className="h-5 w-5 text-indigo-400" />
                          <span>Live Orchestration Stream</span>
                        </h3>
                        <span className="text-xs text-slate-400 font-mono">Status: {isSimulating ? "Processing Agents..." : "Idle"}</span>
                      </div>
                      <div className="space-y-4 max-h-80 overflow-y-auto pr-2">
                        {simulationLogs.map((log, index) => (
                          <div key={index} className="flex items-start space-x-3 text-sm animate-fadeIn">
                            <div className={`mt-0.5 h-6 w-6 rounded-full shrink-0 flex items-center justify-center font-bold text-xs ${
                              log.step === 'SIMULATION_START' || log.step === 'SIMULATION_COMPLETE' ? 'bg-indigo-900 text-indigo-300 border border-indigo-600' :
                              log.step === 'OVERLOAD_DETECTED' || log.step === 'RESOURCE_TRANSFER_FAILED' ? 'bg-rose-950 text-rose-300 border border-rose-600' :
                              log.step === 'RESOURCE_TRANSFER_EXECUTED' || log.step === 'BOOKING_REDIRECT_ACTIVE' ? 'bg-emerald-950 text-emerald-300 border border-emerald-600' :
                              'bg-slate-800 text-slate-300 border border-slate-600'
                            }`}>
                              {index + 1}
                            </div>
                            <div className="space-y-1">
                              <span className="font-mono text-xs text-indigo-400 font-bold uppercase tracking-wider block">{log.step.replace(/_/g, ' ')}</span>
                              <p className="text-slate-200">{log.message}</p>
                              {log.data && log.data.growth_rate && (
                                <div className="text-xs bg-slate-900/50 p-2 rounded border border-slate-800/80 mt-1 font-mono text-slate-400">
                                  Growth Rate: {(log.data.growth_rate*100).toFixed(1)}% | Latest Active Count: {log.data.latest_count}
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 2D Grid Representation of Hospitals Capacity */}
                  <div className="space-y-4">
                    <h3 className="text-xl font-bold text-white">Live Hospital Inventory Grid</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      {hospitals.map(h => {
                        // Check if redirected
                        const isRedirectSource = redirects.some(r => r.source_hospital === h.name);
                        const isRedirectTarget = redirects.some(r => r.target_hospital === h.name);

                        return (
                          <div 
                            key={h.id} 
                            className={`p-6 rounded-2xl border transition duration-300 relative ${
                              isRedirectSource 
                                ? 'border-rose-500 bg-rose-950/20 shadow-lg shadow-rose-950/25' 
                                : isRedirectTarget 
                                  ? 'border-emerald-500 bg-emerald-950/20 shadow-lg shadow-emerald-950/25' 
                                  : 'border-slate-700/60 bg-slate-800/50 hover:bg-slate-800/80'
                            }`}
                          >
                            {/* Proximity badge */}
                            <div className="absolute top-4 right-4 flex space-x-1">
                              {isRedirectSource && (
                                <span className="bg-rose-500 text-white font-bold text-[10px] px-2 py-0.5 rounded-full uppercase tracking-wider animate-pulse flex items-center gap-1">
                                  <AlertCircle className="h-3 w-3" /> Overloaded
                                </span>
                              )}
                              {isRedirectTarget && (
                                <span className="bg-emerald-500 text-white font-bold text-[10px] px-2 py-0.5 rounded-full uppercase tracking-wider flex items-center gap-1">
                                  <CheckCircle className="h-3 w-3" /> Spare Target
                                </span>
                              )}
                            </div>

                            <div className="mb-4">
                              <h4 className="font-bold text-white text-lg pr-16">{h.name}</h4>
                              <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                                <MapPin className="h-3 w-3" /> {h.zone} (Grid: {h.x}, {h.y})
                              </p>
                              <p className="text-xs font-semibold text-indigo-400 mt-0.5">Primary: {h.specialty}</p>
                            </div>

                            {/* Resource indicators */}
                            <div className="grid grid-cols-3 gap-3 border-t border-slate-700/50 pt-4 text-center">
                              <div>
                                <span className="text-[10px] text-slate-400 block uppercase font-bold tracking-wider">Beds</span>
                                <span className={`text-lg font-black ${h.available_beds <= 10 ? 'text-rose-400' : 'text-slate-200'}`}>
                                  {h.available_beds}
                                </span>
                                <span className="text-[10px] text-slate-500 block">/ {h.total_beds}</span>
                              </div>
                              <div>
                                <span className="text-[10px] text-slate-400 block uppercase font-bold tracking-wider">ICU</span>
                                <span className={`text-lg font-black ${h.available_icu <= 2 ? 'text-rose-400' : 'text-slate-200'}`}>
                                  {h.available_icu}
                                </span>
                                <span className="text-[10px] text-slate-500 block">/ {h.total_icu}</span>
                              </div>
                              <div>
                                <span className="text-[10px] text-slate-400 block uppercase font-bold tracking-wider">Vents</span>
                                <span className={`text-lg font-black ${h.available_ventilators <= 1 ? 'text-rose-400' : 'text-slate-200'}`}>
                                  {h.available_ventilators}
                                </span>
                                <span className="text-[10px] text-slate-500 block">/ {h.total_ventilators}</span>
                              </div>
                            </div>

                            {/* Redirection indicator in card */}
                            {isRedirectSource && (
                              <div className="mt-4 p-2 bg-rose-500/10 border border-rose-500/20 rounded-lg flex items-center justify-between text-xs text-rose-300">
                                <span>Booking Redirect Active:</span>
                                <span className="font-bold flex items-center gap-1 text-[11px] text-white bg-rose-600 px-1.5 py-0.5 rounded">
                                  Route to {redirects.find(r => r.source_hospital === h.name)?.target_hospital}
                                </span>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: HOSPITAL FINDER */}
              {activeTab === 'finder' && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                  {/* Left Column - Search Form */}
                  <div className="bg-slate-800/60 p-6 rounded-2xl border border-slate-700/50 shadow-xl space-y-6 self-start">
                    <div>
                      <h3 className="text-xl font-bold text-white mb-2">Search Parameters</h3>
                      <p className="text-xs text-slate-400">Query the finder agent to search clinics and compute exact distances.</p>
                    </div>

                    <form onSubmit={handleFinderSearch} className="space-y-4">
                      <div>
                        <label className="text-xs text-slate-300 font-bold block mb-1">Required Medical Specialty</label>
                        <select 
                          value={finderSpecialty}
                          onChange={(e) => setFinderSpecialty(e.target.value)}
                          className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                        >
                          <option value="">Any Specialty / General Clinic</option>
                          <option value="General Medicine">General Medicine</option>
                          <option value="Cardiology">Cardiology</option>
                          <option value="Pulmonology">Pulmonology</option>
                          <option value="Infectious Diseases">Infectious Diseases</option>
                        </select>
                      </div>

                      {/* Location Grids coordinates */}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="text-xs text-slate-300 font-bold block mb-1">Your Grid X (0-100)</label>
                          <input 
                            type="number"
                            value={finderX}
                            onChange={(e) => setFinderX(e.target.value)}
                            min="0"
                            max="100"
                            className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                          />
                        </div>
                        <div>
                          <label className="text-xs text-slate-300 font-bold block mb-1">Your Grid Y (0-100)</label>
                          <input 
                            type="number"
                            value={finderY}
                            onChange={(e) => setFinderY(e.target.value)}
                            min="0"
                            max="100"
                            className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                          />
                        </div>
                      </div>

                      <div className="space-y-3 pt-2">
                        <span className="text-xs text-slate-300 font-bold block">Minimum Required Equipment Available</span>
                        
                        <div className="grid grid-cols-3 gap-2">
                          <div>
                            <label className="text-[10px] text-slate-400 block mb-0.5 uppercase">Beds</label>
                            <input 
                              type="number"
                              value={finderMinBeds}
                              onChange={(e) => setFinderMinBeds(parseInt(e.target.value) || 0)}
                              className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-center text-sm focus:outline-none"
                            />
                          </div>
                          <div>
                            <label className="text-[10px] text-slate-400 block mb-0.5 uppercase">ICU Beds</label>
                            <input 
                              type="number"
                              value={finderMinIcu}
                              onChange={(e) => setFinderMinIcu(parseInt(e.target.value) || 0)}
                              className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-center text-sm focus:outline-none"
                            />
                          </div>
                          <div>
                            <label className="text-[10px] text-slate-400 block mb-0.5 uppercase">Vents</label>
                            <input 
                              type="number"
                              value={finderMinVents}
                              onChange={(e) => setFinderMinVents(parseInt(e.target.value) || 0)}
                              className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-center text-sm focus:outline-none"
                            />
                          </div>
                        </div>
                      </div>

                      <button 
                        type="submit"
                        className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 rounded-xl font-bold text-sm text-white shadow-lg transition duration-200 mt-4"
                      >
                        Search Closest Hospitals
                      </button>
                    </form>
                  </div>

                  {/* Right Column - Results list */}
                  <div className="lg:col-span-2 space-y-6">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xl font-bold text-white">Closest Hospital Results</h3>
                      <span className="text-xs text-slate-400">Sorted by distance from ({finderX}, {finderY})</span>
                    </div>

                    <div className="space-y-4">
                      {finderResults.length === 0 ? (
                        <div className="bg-slate-800/30 border border-slate-800 p-12 text-center rounded-2xl">
                          <p className="text-slate-400">No clinics match the search filters. Try reducing minimum equipment bounds.</p>
                        </div>
                      ) : (
                        finderResults.map(h => (
                          <div 
                            key={h.id} 
                            className="bg-slate-800/40 border border-slate-700/60 p-6 rounded-2xl flex flex-col md:flex-row justify-between items-start md:items-center gap-6 hover:bg-slate-800/70 transition"
                          >
                            <div className="space-y-2">
                              <div className="flex items-center space-x-2">
                                <h4 className="font-bold text-white text-lg">{h.name}</h4>
                                <span className="bg-indigo-900/60 text-indigo-300 font-mono text-xs px-2.5 py-0.5 rounded-full font-bold">
                                  {h.distance} grid units away
                                </span>
                              </div>
                              <p className="text-xs text-slate-400 flex items-center gap-1">
                                <MapPin className="h-3.5 w-3.5" /> Zone: {h.zone} (Coords: {h.x}, {h.y})
                              </p>
                              <p className="text-xs text-indigo-400 font-semibold">Specialty: {h.specialty}</p>

                              {/* Small capacity indicators */}
                              <div className="flex space-x-4 text-[11px] text-slate-300 pt-2">
                                <span>Beds: <strong className="text-white">{h.available_beds}</strong>/{h.total_beds}</span>
                                <span>ICU: <strong className="text-white">{h.available_icu}</strong>/{h.total_icu}</span>
                                <span>Vents: <strong className="text-white">{h.available_ventilators}</strong>/{h.total_ventilators}</span>
                              </div>
                            </div>

                            <button
                              onClick={() => {
                                // Switch to booking tab and auto-fill doctor of this hospital if possible
                                setActiveTab('bookings');
                                const firstDocOfHosp = doctors.find(d => d.hospital_id === h.id);
                                if (firstDocOfHosp) {
                                  setSelectedDoctorId(firstDocOfHosp.id.toString());
                                }
                              }}
                              className="w-full md:w-auto px-5 py-2.5 bg-indigo-600 hover:bg-indigo-505 bg-indigo-600/90 hover:bg-indigo-600 rounded-lg text-xs font-bold text-white shrink-0 tracking-wider uppercase transition"
                            >
                              Book Doctor
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 3: TRIAGE CHATBOT */}
              {activeTab === 'triage' && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                  {/* Chat interface */}
                  <div className="lg:col-span-2 bg-[#1e293b] rounded-2xl border border-slate-700/60 shadow-2xl flex flex-col h-[600px] overflow-hidden">
                    {/* Disclaimer header */}
                    <div className="bg-rose-950/40 border-b border-rose-500/20 p-4 flex items-start space-x-3 text-xs text-rose-300">
                      <AlertTriangle className="h-5 w-5 shrink-0 text-rose-400" />
                      <p>
                        <strong>CRITICAL DISCLAIMER:</strong> This chatbot is Gemini-powered for medical triage guidance and appointment steering only. It does NOT provide formal diagnoses. **For acute emergencies or chest pains, go to an Emergency Room immediately.**
                      </p>
                    </div>

                    {/* Messages panel */}
                    <div className="flex-1 p-6 overflow-y-auto space-y-4 bg-slate-900/30">
                      {chatHistory.map((msg, index) => (
                        <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                          <div className={`max-w-[80%] rounded-2xl p-4 text-sm leading-relaxed ${
                            msg.role === 'user' 
                              ? 'bg-indigo-600 text-white rounded-br-none' 
                              : 'bg-slate-800 border border-slate-700/80 text-slate-200 rounded-bl-none shadow-md'
                          }`}>
                            <p className="whitespace-pre-line">{msg.text}</p>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Input bar */}
                    <form onSubmit={handleSendChatMessage} className="p-4 border-t border-slate-700 bg-slate-800/80 flex items-center space-x-3">
                      <input 
                        type="text"
                        placeholder="Describe your symptoms (e.g. cough, fever, heart fluttering)..."
                        value={chatMessage}
                        onChange={(e) => setChatMessage(e.target.value)}
                        className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                      />
                      <button 
                        type="submit"
                        className="p-3 bg-indigo-600 hover:bg-indigo-500 rounded-xl text-white shadow-lg transition"
                      >
                        <MessageSquare className="h-5 w-5" />
                      </button>
                    </form>
                  </div>

                  {/* AI Triage Side panel */}
                  <div className="space-y-6">
                    <div className="bg-slate-800/60 p-6 rounded-2xl border border-slate-700/50 shadow-xl space-y-4">
                      <h3 className="text-xl font-bold text-white">Triage Agent Output</h3>
                      <p className="text-xs text-slate-400">The agent extracts matching fields from your consultation to route booking.</p>
                      
                      <div className="border-t border-slate-700/50 pt-4 space-y-3">
                        <div>
                          <span className="text-[10px] text-slate-400 block uppercase font-bold tracking-wider mb-1">Inferred Urgency</span>
                          {triageSuggestion ? (
                            <span className={`px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider inline-block ${
                              triageSuggestion.level === 'Urgent' ? 'bg-rose-500/20 text-rose-300' :
                              triageSuggestion.level === 'Semi-urgent' ? 'bg-amber-500/20 text-amber-300' :
                              'bg-emerald-500/20 text-emerald-300'
                            }`}>
                              {triageSuggestion.level} Urgency
                            </span>
                          ) : (
                            <span className="text-slate-500 text-xs italic">Waiting for chat input...</span>
                          )}
                        </div>

                        <div>
                          <span className="text-[10px] text-slate-400 block uppercase font-bold tracking-wider mb-1">Clinic Specialty Suggested</span>
                          {triageSuggestion ? (
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-white text-sm">{triageSuggestion.specialty}</span>
                              <button
                                onClick={() => {
                                  setActiveTab('finder');
                                  setFinderSpecialty(triageSuggestion.specialty);
                                }}
                                className="text-xs text-indigo-400 hover:underline flex items-center gap-1 font-bold"
                              >
                                Find Hospital <ArrowRight className="h-3 w-3" />
                              </button>
                            </div>
                          ) : (
                            <span className="text-slate-500 text-xs italic">Waiting for chat input...</span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="bg-indigo-950/20 border border-indigo-900/30 p-6 rounded-2xl space-y-2">
                      <h4 className="font-bold text-indigo-400 text-sm flex items-center gap-2">
                        <BriefcaseMedical className="h-4 w-4" />
                        <span>Triage Smart Links</span>
                      </h4>
                      <p className="text-xs text-slate-400 leading-relaxed">
                        If the AI recommends a specialized clinic, use these buttons to auto-configure searches:
                      </p>
                      <div className="grid grid-cols-2 gap-2 pt-2">
                        <button 
                          onClick={() => { setActiveTab('finder'); setFinderSpecialty('Cardiology'); }}
                          className="bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/60 p-2 text-center rounded-lg text-xs font-semibold text-slate-300 transition"
                        >
                          Cardiology Finder
                        </button>
                        <button 
                          onClick={() => { setActiveTab('finder'); setFinderSpecialty('Pulmonology'); }}
                          className="bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/60 p-2 text-center rounded-lg text-xs font-semibold text-slate-300 transition"
                        >
                          Pulmonology Finder
                        </button>
                        <button 
                          onClick={() => { setActiveTab('finder'); setFinderSpecialty('Infectious Diseases'); }}
                          className="bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/60 p-2 text-center rounded-lg text-xs font-semibold text-slate-300 transition"
                        >
                          Infectious Finder
                        </button>
                        <button 
                          onClick={() => { setActiveTab('bookings'); }}
                          className="bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/60 p-2 text-center rounded-lg text-xs font-semibold text-slate-300 transition"
                        >
                          Doctor Schedules
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 4: BOOKINGS & REDIRECTION STATUS */}
              {activeTab === 'bookings' && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                  {/* Left Column - Booking Form */}
                  <div className="bg-slate-800/60 p-6 rounded-2xl border border-slate-700/50 shadow-xl space-y-6 self-start">
                    <div>
                      <h3 className="text-xl font-bold text-white mb-2">Book Appointment</h3>
                      <p className="text-xs text-slate-400">Select a doctor schedule. Active redirects will be processed automatically.</p>
                    </div>

                    <form onSubmit={handleBookAppointment} className="space-y-4">
                      <div>
                        <label className="text-xs text-slate-300 font-bold block mb-1">Patient Full Name</label>
                        <input 
                          type="text"
                          placeholder="e.g. Sarah Jenkins"
                          value={patientName}
                          onChange={(e) => setPatientName(e.target.value)}
                          className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                        />
                      </div>

                      <div>
                        <label className="text-xs text-slate-300 font-bold block mb-1">Select Doctor & specialty</label>
                        <select 
                          value={selectedDoctorId}
                          onChange={(e) => {
                            setSelectedDoctorId(e.target.value);
                            setSelectedSlot('');
                          }}
                          className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                        >
                          <option value="">-- Choose Doctor --</option>
                          {doctors.map(d => (
                            <option key={d.id} value={d.id}>
                              {d.name} ({d.specialty} - {d.hospital_name})
                            </option>
                          ))}
                        </select>
                      </div>

                      {selectedDoctorId && (
                        <div>
                          <label className="text-xs text-slate-300 font-bold block mb-1">Available Slots</label>
                          <div className="grid grid-cols-3 gap-2">
                            {getDoctorSlots().length === 0 ? (
                              <span className="text-xs text-rose-400 italic col-span-3">No remaining slots for this doctor today.</span>
                            ) : (
                              getDoctorSlots().map(slot => (
                                <button
                                  key={slot}
                                  type="button"
                                  onClick={() => setSelectedSlot(slot)}
                                  className={`p-2 rounded-lg text-xs font-semibold text-center border transition ${
                                    selectedSlot === slot 
                                      ? 'bg-indigo-600 border-indigo-400 text-white shadow' 
                                      : 'bg-slate-900 border-slate-700 hover:border-slate-500 text-slate-300'
                                  }`}
                                >
                                  {slot}
                                </button>
                              ))
                            )}
                          </div>
                        </div>
                      )}

                      <button 
                        type="submit"
                        className="w-full py-3 bg-indigo-600 hover:bg-indigo-505 bg-indigo-600/90 hover:bg-indigo-600 rounded-xl font-bold text-sm text-white shadow-lg transition"
                      >
                        Confirm Booking
                      </button>
                    </form>

                    {bookingMessage && (
                      <div className={`p-4 rounded-xl border text-xs leading-relaxed ${
                        bookingMessage.success 
                          ? 'bg-emerald-950/20 border-emerald-500/20 text-emerald-300' 
                          : 'bg-rose-950/20 border-rose-500/20 text-rose-300'
                      }`}>
                        <div className="font-bold flex items-center gap-1 mb-1">
                          {bookingMessage.success ? <CheckCircle className="h-4 w-4 text-emerald-400" /> : <AlertCircle className="h-4 w-4 text-rose-400" />}
                          {bookingMessage.success ? "Booking Confirmed!" : "Booking Error"}
                        </div>
                        <p>{bookingMessage.message}</p>
                        {bookingMessage.success && bookingMessage.details && (
                          <div className="mt-2 pt-2 border-t border-emerald-500/10 font-mono text-[10px] space-y-0.5">
                            <div>Doctor: {bookingMessage.details.doctor_name}</div>
                            <div>Hospital: {bookingMessage.details.hospital_name}</div>
                            <div>Time Slot: {bookingMessage.details.time_slot}</div>
                            <div>Status: <span className="underline font-bold">{bookingMessage.details.status}</span></div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Middle Column - Active Redirections */}
                  <div className="space-y-6">
                    <h3 className="text-xl font-bold text-white flex items-center gap-2">
                      <Shuffle className="h-5 w-5 text-amber-400" />
                      <span>Active Redirection Rules</span>
                    </h3>
                    <p className="text-xs text-slate-400">Rules configured by the Orchestrator to balance clinic loads during surges.</p>

                    <div className="space-y-4">
                      {redirects.length === 0 ? (
                        <div className="bg-slate-800/30 border border-slate-800 p-6 rounded-2xl text-center">
                          <p className="text-slate-500 text-xs italic">No active patient redirection rules. System operating under normal parameters.</p>
                        </div>
                      ) : (
                        redirects.map(rule => (
                          <div key={rule.id} className="bg-amber-950/20 border border-amber-500/30 p-5 rounded-2xl space-y-3">
                            <div className="flex items-center justify-between text-xs text-amber-400 font-bold uppercase tracking-wider">
                              <span>Redirection Code {rule.id}</span>
                              <span className="bg-amber-500 text-slate-900 font-extrabold px-1.5 py-0.5 rounded">Active</span>
                            </div>
                            <div className="flex items-center space-x-3 text-sm text-white">
                              <span className="font-semibold text-rose-300">{rule.source_hospital}</span>
                              <ArrowRight className="h-4 w-4 text-slate-400" />
                              <span className="font-semibold text-emerald-300">{rule.target_hospital}</span>
                            </div>
                            <p className="text-[11px] text-slate-400 leading-relaxed">
                              All booking requests for doctors at {rule.source_hospital} are currently redirected to doctors with identical specialty profiles at {rule.target_hospital}.
                            </p>
                          </div>
                        ))
                      )}
                    </div>

                    {/* Resource transfers logs inside booking page too */}
                    <div className="space-y-4">
                      <h4 className="font-bold text-white text-sm">Resource Transfer Log</h4>
                      <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                        {transfers.length === 0 ? (
                          <p className="text-slate-500 text-xs italic">No resource transfers executed yet.</p>
                        ) : (
                          transfers.map(t => (
                            <div key={t.id} className="bg-slate-900/50 p-3 rounded-lg border border-slate-800/80 text-[11px] flex justify-between items-center">
                              <div>
                                <span className="font-bold text-white">{t.quantity} {t.equipment_type}</span>
                                <span className="text-slate-400 block">From {t.source_hospital}</span>
                                <span className="text-slate-400 block">To {t.target_hospital}</span>
                              </div>
                              <span className="text-slate-500 font-mono text-[9px]">{new Date(t.timestamp).toLocaleTimeString()}</span>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Right Column - Booking list */}
                  <div className="space-y-6">
                    <h3 className="text-xl font-bold text-white">Recent Confirmed Appointments</h3>
                    <p className="text-xs text-slate-400">List of bookings recorded by the system.</p>

                    <div className="space-y-4 max-h-[500px] overflow-y-auto pr-1">
                      {bookings.length === 0 ? (
                        <div className="bg-slate-800/30 border border-slate-800 p-8 text-center rounded-2xl">
                          <p className="text-slate-500 text-xs">No active appointments booked yet.</p>
                        </div>
                      ) : (
                        bookings.map(b => (
                          <div 
                            key={b.id} 
                            className={`p-4 rounded-xl border ${
                              b.status === 'Redirected' 
                                ? 'bg-amber-950/10 border-amber-500/20' 
                                : 'bg-slate-800/50 border-slate-700/60'
                            }`}
                          >
                            <div className="flex justify-between items-start mb-2">
                              <span className="font-bold text-white text-sm">{b.patient_name}</span>
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                                b.status === 'Redirected' ? 'bg-amber-500/20 text-amber-300' : 'bg-emerald-500/20 text-emerald-300'
                              }`}>
                                {b.status}
                              </span>
                            </div>
                            <div className="text-xs text-slate-300 space-y-1 font-mono">
                              <div>Dr: {b.doctor_name}</div>
                              <div>Hosp: {b.hospital_name}</div>
                              <div>Time: {b.time_slot}</div>
                              {b.original_hospital_name && (
                                <div className="text-amber-400 text-[10px] pt-1">
                                  * Redirected from: {b.original_hospital_name}
                                </div>
                              )}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

        </div>
      </main>

    </div>
  );
}
