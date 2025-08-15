const API_BASE_URL = "https://your-render-backend.onrender.com";

import { useState, useEffect } from "react";
import "./App.css";

function App() {
  // VIEW STATE
  const [view, setView] = useState("chat"); // 'chat', 'form', or 'dashboard'

  //  CHAT STATE
  const [messages, setMessages] = useState([
    { sender: "assistant", text: "Hello! How can I help you today?" }
  ]);
  const [input, setInput] = useState("");
  
  //  FORM STATE
  const [doctors, setDoctors] = useState([]);
  const [selectedDoctor, setSelectedDoctor] = useState("any");
  const [date, setDate] = useState(new Date().toISOString().split("T")[0]);
  const [time, setTime] = useState("");
  const [email, setEmail] = useState("");
  const [symptoms, setSymptoms] = useState("");

  // SHARED & DASHBOARD STATE
  const [response, setResponse] = useState("");
  const [dashboardReport, setDashboardReport] = useState("");
  const [selectedDoctorForReport, setSelectedDoctorForReport] = useState(""); // <-- NEW: State for dashboard doctor selection
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(
    `session_${Date.now()}_${Math.random().toString(36).substring(2)}`
  );

  // Fetch doctors list for the form and dashboard on component mount
  useEffect(() => {
    const fetchDoctors = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/doctors`);
        if (!res.ok) throw new Error("Failed to fetch doctors list");
        const data = await res.json();
        setDoctors(data);
        if (data.length > 0) {
          setSelectedDoctorForReport(data[0].name); // Default to the first doctor for the dashboard
        }
      } catch (err) {
        console.error(err);
        setMessages(prev => [...prev, { sender: "assistant", text: `Error: Could not load doctor list. ${err.message}` }]);
      }
    };
    fetchDoctors();
  }, []);

  // Generic function to send a prompt to the CHAT backend
  const sendPromptToBackend = async (prompt) => {
    setIsLoading(true);
    setResponse(""); 
    setDashboardReport("");
    try {
      const res = await fetch(`${API_BASE_URL}/chat`,  {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: prompt, session_id: sessionId }),
      });
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      const data = await res.json();
      return data.reply;
    } catch (err) {
      return `Error: ${err.message}`;
    } finally {
      setIsLoading(false);
    }
  };

  // Handle chat message submission
  const handleChatSend = async () => {
    if (!input.trim()) return;
    const userMessage = { sender: "user", text: input };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    
    const assistantReplyText = await sendPromptToBackend(input);
    const assistantMessage = { sender: "assistant", text: assistantReplyText };
    setMessages(prev => [...prev, assistantMessage]);
  };

  // Handle form submission to the new /book endpoint
  const handleFormSubmit = async (e) => {
    e.preventDefault();
    if (!time || !email) {
      setResponse("Please fill in both the time and your email address.");
      return;
    }
    setIsLoading(true);
    setResponse("");

    const doctorName = selectedDoctor === "any" ? "any" : doctors.find(d => d.id === parseInt(selectedDoctor))?.name || "any";

    const bookingDetails = {
      doctor_name: doctorName,
      date: date,
      time: time,
      email: email,
      symptoms: symptoms
    };

    try {
      const res = await fetch(`${API_BASE_URL}/book`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bookingDetails),
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || `HTTP error! status: ${res.status}`);
      }
      const data = await res.json();
      setResponse(data.reply);
    } catch (err) {
      setResponse(`Error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle dashboard button clicks with selected doctor context
  const handleDashboardQuery = async (query) => {
    if (!selectedDoctorForReport) {
      setDashboardReport("Please select a doctor first.");
      return;
    }
    const fullQuery = `${query} for ${selectedDoctorForReport}`;
    const report = await sendPromptToBackend(fullQuery);
    setDashboardReport(report);
  };

  // RENDER LOGIC
  return (
    <div className="app">
      <h1>Smart Doctor Assistant</h1>
      
      <div className="view-switcher">
        <button onClick={() => setView("chat")} className={view === "chat" ? "active" : ""}>Chat Assistant</button>
        <button onClick={() => setView("form")} className={view === "form" ? "active" : ""}>Book with Form</button>
        <button onClick={() => setView("dashboard")} className={view === "dashboard" ? "active" : ""}>Doctor Dashboard</button>
      </div>

      {view === 'dashboard' && (
        <div className="dashboard-container">
          <h2>Quick Reports</h2>
          
          {/* --- NEW: Doctor Selector Dropdown --- */}
          <div className="form-group">
            <label htmlFor="doctor-report">Select Doctor for Report</label>
            <select 
              id="doctor-report" 
              value={selectedDoctorForReport} 
              onChange={(e) => setSelectedDoctorForReport(e.target.value)}
            >
              {doctors.map((doc) => (
                <option key={doc.id} value={doc.name}>
                  {doc.name}
                </option>
              ))}
            </select>
          </div>
          {/* END: Doctor Selector */}

          <div className="dashboard-buttons">
            <button onClick={() => handleDashboardQuery("how many appointments do I have today?")} disabled={isLoading}>Today's Summary</button>
            <button onClick={() => handleDashboardQuery("how many patients visited yesterday?")} disabled={isLoading}>Yesterday's Summary</button>
            <button onClick={() => handleDashboardQuery("how many patients with fever?")} disabled={isLoading}>Fever Case Summary</button>
          </div>
          {dashboardReport && (
            <div className="response-area">
              <h3>Report Result:</h3>
              <p>{dashboardReport}</p>
            </div>
          )}
        </div>
      )}

      {view === "chat" && (
        <div className="chat-container">
          <div className="chat-box">
            {messages.map((m, i) => (
              <div key={i} className={`message ${m.sender}`}>
                <p><strong>{m.sender === 'user' ? 'You' : 'Assistant'}:</strong> {m.text}</p>
              </div>
            ))}
          </div>
          <div className="input-area">
            <input
              type="text"
              placeholder="Type a message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleChatSend()}
              disabled={isLoading}
            />
            <button onClick={handleChatSend} disabled={isLoading}>
              {isLoading ? "Thinking..." : "Send"}
            </button>
          </div>
        </div>
      )}

      {view === "form" && (
        <div className="form-container">
           <p className="subtitle">Book Your Appointment Directly</p>
          <form className="booking-form" onSubmit={handleFormSubmit}>
            <div className="form-group">
              <label htmlFor="symptoms">Briefly describe your symptoms (optional)</label>
              <input id="symptoms" type="text" value={symptoms} onChange={(e) => setSymptoms(e.target.value)} placeholder="e.g., fever, skin rash, chest pain" />
            </div>
            <div className="form-group">
              <label htmlFor="doctor">Select a Doctor</label>
              <select id="doctor" value={selectedDoctor} onChange={(e) => setSelectedDoctor(e.target.value)}>
                <option value="any">Any Available Doctor</option>
                {doctors.map((doc) => <option key={doc.id} value={doc.id}>{doc.name} ({doc.specialization})</option>)}
              </select>
            </div>
            <div className="form-group">
              <label htmlFor="date">Date</label>
              <input id="date" type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
            </div>
            <div className="form-group">
              <label htmlFor="time">Time</label>
              <input id="time" type="text" value={time} onChange={(e) => setTime(e.target.value)} placeholder="e.g., 5 PM or 17:00" required />
            </div>
            <div className="form-group">
              <label htmlFor="email">Your Email Address</label>
              <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@example.com" required />
            </div>
            <button type="submit" disabled={isLoading}>
              {isLoading ? "Booking..." : "Book Appointment"}
            </button>
          </form>
          {response && (
            <div className="response-area">
              <h3>Assistant's Reply:</h3>
              <p>{response}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
