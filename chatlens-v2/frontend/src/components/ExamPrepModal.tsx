"use client";

import { useState } from "react";
import { X, BookOpen, Search, CheckCircle, Cpu, HelpCircle, Calendar, MapPin } from "lucide-react";

interface ExamPrepModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const EXAM_SCHEDULE = [
  {
    course: "Embedded System Design & IoT (25EC2206E)",
    event: "Lab In-Sem Examination",
    date: "15 Oct 2026",
    time: "10:00 AM – 11:40 AM (P3-P4)",
    section: "S-10",
    room: "103",
    faculty: "Dr. Dinesh Kumar",
    technician: "None listed",
  },
  {
    course: "Embedded System Design & IoT (25EC2206E)",
    event: "Project Defence & Demonstration",
    date: "16 Oct 2026",
    time: "10:00 AM – 11:40 AM (P3-P4)",
    section: "S-10",
    room: "14D",
    faculty: "Dr. Dinesh Kumar",
    technician: "Ms. Swathi",
  },
];

const EXPERIMENTS = [
  {
    id: 1,
    title: "Two LEDs Blinking",
    task: "Blink two LEDs continuously at 1s interval using digital output pins (Pins 12, 13).",
    viva: [
      "Role of transmit buffers, receive FIFOs, and acceptance filters in STM32H7 FDCAN peripheral?",
      "Common CAN bit rates: 250 kbps, 500 kbps, 1 Mbps.",
    ],
  },
  {
    id: 2,
    title: "LED Control via Push Button",
    task: "Control LED with momentary push button (Pins 2, 12 with INPUT_PULLUP).",
    viva: [
      "Role of a CAN transceiver between MCU and bus: converts TTL logic levels to differential voltage signals.",
      "Purpose of CRC field in CAN: transmission integrity & error detection.",
    ],
  },
  {
    id: 3,
    title: "LED Brightness via Potentiometer (PWM)",
    task: "Read analog value from potentiometer on A0 and map to PWM output on Pin 9 (0-255).",
    viva: [
      "Why 120Ω termination resistors are used in CAN: impedance matching to prevent signal reflections.",
      "Nyquist criterion: sampling frequency must be at least 2× the maximum signal frequency.",
    ],
  },
  {
    id: 4,
    title: "Light Intensity Measurement using LDR",
    task: "Measure surrounding light using LDR voltage divider on A0 and print lux condition to Serial Monitor.",
    viva: [
      "Purpose of ACK field in CAN: receiving nodes acknowledge valid frame reception.",
      "Error frames in CAN: nodes overwrite bus on CRC/bit error to trigger automatic retransmission.",
    ],
  },
  {
    id: 5,
    title: "Distance Measurement using Ultrasonic Sensor",
    task: "HC-SR04 pulse duration measurement and convert to cm on Serial Monitor.",
    viva: [
      "PID terms contribution: P proportional to current error, I eliminates steady-state error, D predicts future trends.",
      "Classical CAN data payload capacity: up to 8 bytes (compared to 64 bytes in CAN FD).",
    ],
  },
  {
    id: 6,
    title: "Human Movement Detection using PIR Sensor",
    task: "Digital read PIR sensor and output Motion Detected / No Motion.",
    viva: [
      "Command vs Telemetry vs Heartbeat in CAN: command instructs an actuator, telemetry reports sensor telemetry, heartbeat broadcasts node health.",
      "Data frame vs Remote frame: data frame carries payload; remote frame requests transmission of specific identifier.",
    ],
  },
  {
    id: 7,
    title: "Servo Motor Angular Sweep",
    task: "Sweep servo from 0° to 180° and return with step delays.",
    viva: [
      "Bumpless transfer: smooth transition between manual and automatic PID control without actuator spikes.",
      "DLC (Data Length Code): indicates payload size in bytes within the CAN frame.",
    ],
  },
  {
    id: 8,
    title: "16x2 I2C LCD Interfacing",
    task: "Display Name on Row 1 and Roll Number on Row 2 via I2C address (0x27 or 0x3F).",
    viva: [
      "Discrete-time PID sampling period: critical for stable numerical integration without jitter.",
      "CAN arbitration: lower numerical identifier dominates the bus (dominant bit 0 wins over recessive 1).",
    ],
  },
  {
    id: 9,
    title: "Temperature Measurement using Thermistor",
    task: "10k NTC thermistor (Beta=3950) on Pin A1 with 10k resistor divider to measure temperature in Celsius.",
    viva: [
      "CAN applications: automotive ECUs, avionics, industrial automation, medical robotics.",
      "CAN message priority: assign lower numerical IDs to mission-critical or emergency signals.",
    ],
  },
];

export default function ExamPrepModal({ isOpen, onClose }: ExamPrepModalProps) {
  const [filter, setFilter] = useState("");

  if (!isOpen) return null;

  const filteredExperiments = filter
    ? EXPERIMENTS.filter(
        (exp) =>
          exp.title.toLowerCase().includes(filter.toLowerCase()) ||
          exp.task.toLowerCase().includes(filter.toLowerCase()) ||
          exp.viva.some((v) => v.toLowerCase().includes(filter.toLowerCase()))
      )
    : EXPERIMENTS;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-4xl max-h-[85vh] flex flex-col rounded-brand bg-brand-bg border border-brand-border shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-brand-border bg-gradient-to-r from-purple-500/10 via-brand-accent/10 to-transparent">
          <div className="flex items-center gap-2.5">
            <BookOpen className="text-purple-400" size={22} />
            <div>
              <h2 className="text-base font-semibold text-brand-text-bright">
                Academic Intel · In-Sem Lab Exam & Viva Preparation
              </h2>
              <p className="text-xs text-brand-text-dim">
                Section S-10 schedules, Arduino experiments, and 18 verified viva question sets
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-brand-sm text-brand-text-dim hover:text-brand-text hover:bg-white/5 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          {/* Exam Schedule Cards */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-purple-400 mb-3 flex items-center gap-1.5">
              <Calendar size={14} /> Confirmed Exam & Defence Sessions
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {EXAM_SCHEDULE.map((exam, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-brand-sm border border-purple-500/20 bg-purple-500/5 flex flex-col justify-between"
                >
                  <div>
                    <span className="text-[0.65rem] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-purple-500/20 text-purple-300">
                      Section {exam.section}
                    </span>
                    <h4 className="text-sm font-semibold text-brand-text-bright mt-2">
                      {exam.event}
                    </h4>
                    <p className="text-xs text-brand-text-dim mt-0.5">{exam.course}</p>
                  </div>
                  <div className="mt-4 pt-3 border-t border-purple-500/15 space-y-1 text-xs">
                    <div className="flex items-center gap-2 text-brand-text">
                      <Calendar size={13} className="text-purple-400 shrink-0" />
                      <span>{exam.date} · {exam.time}</span>
                    </div>
                    <div className="flex items-center gap-2 text-brand-text">
                      <MapPin size={13} className="text-brand-accent shrink-0" />
                      <span>Room <strong className="text-brand-text-bright">{exam.room}</strong> · Faculty: {exam.faculty}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Search bar */}
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-brand-text-dim" />
            <input
              type="text"
              placeholder="Filter experiments, topics, or viva questions (e.g. CAN bus, thermistor, PWM)..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="w-full pl-9 pr-3 py-2 rounded-brand-sm border border-brand-border bg-brand-card text-xs text-brand-text outline-none focus:border-purple-400 transition-colors placeholder-brand-text-dim"
            />
          </div>

          {/* Experiments List */}
          <div className="space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-brand-accent flex items-center gap-1.5">
              <Cpu size={14} /> 9 Practical Experiments & Viva Q&A
            </h3>
            {filteredExperiments.map((exp) => (
              <div
                key={exp.id}
                className="p-4 rounded-brand-sm border border-brand-border bg-brand-card/50 hover:bg-brand-card transition-colors space-y-2.5"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-brand-accent/15 text-brand-accent text-[0.65rem] font-bold flex items-center justify-center shrink-0">
                      {exp.id}
                    </span>
                    <h4 className="text-sm font-medium text-brand-text-bright">{exp.title}</h4>
                  </div>
                  <CheckCircle size={14} className="text-emerald-400 shrink-0 mt-0.5" />
                </div>
                <p className="text-xs text-brand-text-dim pl-7">{exp.task}</p>
                <div className="pl-7 pt-2 border-t border-brand-border/40 space-y-1.5">
                  <span className="text-[0.65rem] font-bold uppercase tracking-wider text-purple-400 flex items-center gap-1">
                    <HelpCircle size={11} /> Verified Viva Questions:
                  </span>
                  {exp.viva.map((v, i) => (
                    <p key={i} className="text-xs text-brand-text leading-relaxed">
                      • {v}
                    </p>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 px-5 border-t border-brand-border bg-brand-card/30 flex items-center justify-between text-xs text-brand-text-dim">
          <span>Synced with Telegram document intelligence & TurboVec index</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-brand-sm bg-purple-500/20 text-purple-300 hover:bg-purple-500/30 transition-colors font-medium text-xs"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
