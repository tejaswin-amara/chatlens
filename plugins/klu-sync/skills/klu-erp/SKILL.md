---
name: klu-erp
description: Access real-time student ERP data from KL University (attendance, internal marks, fee payments, and timetable overrides). Triggered by natural language requests or /klu-erp.
---

# KL University ERP Integration (KLU ERP)

This skill enables querying academic metrics directly from the KL University student portal (`https://newerp.kluniversity.in`) and the SPARK PA daemon.

## Features
- **Attendance & Safe Bunk Margins**: Real-time attended/conducted class hours, distinction cutoff (85%), and safe bunks left before condonation.
- **In-Sem Assessment Marks**: Internal marks breakdown across Mid-1, Lab In-Sems, surprise tests, quizzes, and project evaluations.
- **Fee Orders & Receipts**: Outstanding fee balances, order IDs, and payment verification receipts.
- **Dynamic Timetable Overrides**: Room shifts, cancellations, and special schedules merged from student group chats.

## Available Bot Commands
When interacting with `@Tejaswin_Amara_PA_bot`:
- `/today` — Today's classes with room overrides and cancellations highlighted.
- `/attendance` — Live attendance table with safe bunk calculations.
- `/marks` — In-sem internal assessment evaluations.
- `/fee` — Fee orders and payment receipts.
- `/rescan` — Deep multimodal catch-up across group chats for the past 7 days.
- `/status` — Live status of Telegram, Gemini AI, and ERP bridge.
