process.env.KL_SYNC_DEMO_MODE = process.env.KL_SYNC_DEMO_MODE || 'true';
process.env.KL_SYNC_AI_MODE = process.env.KL_SYNC_AI_MODE || 'offline';
process.env.SESSION_SECRET =
  process.env.SESSION_SECRET || 'ci-secret-key-testing-minimum-32-bytes-long';

import { NextRequest } from 'next/server';
import { POST as handleAiChat } from '../src/app/api/ai/chat/route';
import {
  TOOLS_REGISTRY,
  getAttendanceArgsSchema,
  calculateAttendanceTargetArgsSchema,
  predictCGPAArgsSchema,
} from '../src/lib/ai/tools';
import {
  executeTool,
  executeCalculateAttendanceTarget,
  executePredictCGPA,
  processAIChat,
} from '../src/lib/ai/executor';

interface JudgeTestCase {
  id: string;
  category: string;
  name: string;
  fn: () => Promise<void>;
}

const testResults: Array<{
  id: string;
  name: string;
  category: string;
  passed: boolean;
  durationMs: number;
  error?: string;
}> = [];

function registerTest(
  id: string,
  category: string,
  name: string,
  fn: () => Promise<void>
): JudgeTestCase {
  return { id, category, name, fn };
}

const cases: JudgeTestCase[] = [
  // 1. Tool Registry Verification
  registerTest(
    'AJ-01',
    'AI Schema & Registry',
    'Verify Agent Tool Definitions in Registry',
    async () => {
      if (!Array.isArray(TOOLS_REGISTRY) || TOOLS_REGISTRY.length !== 7) {
        throw new Error(
          `Expected 7 tools in TOOLS_REGISTRY, got ${TOOLS_REGISTRY.length}`
        );
      }
      const expectedNames = [
        'getAttendance',
        'getTimetable',
        'getMarks',
        'getFeeDetails',
        'getStudentProfile',
        'calculateAttendanceTarget',
        'predictCGPA',
      ];
      for (const name of expectedNames) {
        const found = TOOLS_REGISTRY.find((t) => t.name === name);
        if (!found) throw new Error(`Missing tool definition for ${name}`);
        if (!found.description || typeof found.description !== 'string') {
          throw new Error(`Tool ${name} has invalid description`);
        }
      }
    }
  ),

  // 2. Schema Validation Verification
  registerTest(
    'AJ-02',
    'AI Schema & Registry',
    'Validate Zod Parameter Schemas',
    async () => {
      const attArgs = getAttendanceArgsSchema.parse({ subject: 'OS' });
      if (attArgs.subject !== 'OS')
        throw new Error('getAttendanceArgsSchema failed');

      const targetArgs = calculateAttendanceTargetArgsSchema.parse({
        currentAttended: 30,
        currentTotal: 40,
        targetPercent: 85,
      });
      if (
        targetArgs.currentAttended !== 30 ||
        targetArgs.targetPercent !== 85
      ) {
        throw new Error('calculateAttendanceTargetArgsSchema failed');
      }

      const cgpaArgs = predictCGPAArgsSchema.parse({
        currentCGPA: 8.5,
        completedCredits: 60,
        newCourses: [{ credits: 4, expectedGrade: 'O' }],
      });
      if (
        cgpaArgs.currentCGPA !== 8.5 ||
        cgpaArgs.newCourses[0].expectedGrade !== 'O'
      ) {
        throw new Error('predictCGPAArgsSchema failed');
      }
    }
  ),

  // 3. Natural Language Query Intent Parser
  registerTest(
    'AJ-03',
    'Natural Language Querying',
    'Parse Natural Language Query Intents',
    async () => {
      const attRes = await processAIChat([
        { role: 'user', content: 'What is my attendance in OS?' },
      ]);
      if (
        !attRes.toolCalls ||
        attRes.toolCalls.length === 0 ||
        attRes.toolCalls[0].tool !== 'getAttendance' ||
        attRes.toolCalls[0].args.subject !== 'OS'
      ) {
        throw new Error('Failed to parse attendance query intent');
      }

      const feeRes = await processAIChat([
        { role: 'user', content: 'Show my fee breakdown and pending balance' },
      ]);
      if (
        !feeRes.toolCalls ||
        feeRes.toolCalls.length === 0 ||
        feeRes.toolCalls[0].tool !== 'getFeeDetails'
      ) {
        throw new Error('Failed to parse fee query intent');
      }

      const targetRes = await processAIChat([
        {
          role: 'user',
          content: 'How many classes do I need to reach 85% attendance?',
        },
      ]);
      if (
        !targetRes.toolCalls ||
        targetRes.toolCalls.length === 0 ||
        targetRes.toolCalls[0].tool !== 'calculateAttendanceTarget'
      ) {
        throw new Error('Failed to parse target calculation query intent');
      }

      const cgpaRes = await processAIChat([
        { role: 'user', content: 'Predict my CGPA for next semester' },
      ]);
      if (
        !cgpaRes.toolCalls ||
        cgpaRes.toolCalls.length === 0 ||
        cgpaRes.toolCalls[0].tool !== 'predictCGPA'
      ) {
        throw new Error('Failed to parse CGPA prediction query intent');
      }
    }
  ),

  // 4. Execution Engine Tool Call Execution
  registerTest(
    'AJ-04',
    'Tool Execution Engine',
    'Execute getAttendance & getStudentProfile Tools',
    async () => {
      const profileRes = await executeTool('getStudentProfile', {});
      if (!profileRes.success || profileRes.tool !== 'getStudentProfile') {
        throw new Error('executeTool(getStudentProfile) failed');
      }
      const profileData = profileRes.result as {
        profile: { name: string; universityId: string };
      };
      if (!profileData.profile?.name || !profileData.profile?.universityId) {
        throw new Error('Profile tool returned invalid profile data payload');
      }

      const attRes = await executeTool('getAttendance', {
        subject: '23CS2101R',
      });
      if (!attRes.success || attRes.tool !== 'getAttendance') {
        throw new Error('executeTool(getAttendance) failed');
      }
    }
  ),

  // 5. Direct Calculation Tools Execution
  registerTest(
    'AJ-05',
    'Workflow Automation',
    'Execute calculateAttendanceTarget & predictCGPA',
    async () => {
      const targetCalc = executeCalculateAttendanceTarget({
        currentAttended: 33,
        currentTotal: 40,
        targetPercent: 85,
      });
      if (
        !targetCalc.success ||
        targetCalc.currentPercentage !== 82.5 ||
        targetCalc.classesNeeded !== 7
      ) {
        throw new Error(
          `calculateAttendanceTarget calculation error. Expected 7 classes needed, got ${targetCalc.classesNeeded}`
        );
      }

      const cgpaPredict = executePredictCGPA({
        currentCGPA: 8.0,
        completedCredits: 60,
        newCourses: [
          { credits: 4, expectedGrade: 'O' }, // 10 * 4 = 40
          { credits: 4, expectedGrade: 'A+' }, // 9 * 4 = 36
        ],
      });
      // total = (8.0 * 60 + 76) / 68 = (480 + 76) / 68 = 556 / 68 = 8.176 -> 8.18
      if (!cgpaPredict.success || cgpaPredict.predictedCGPA !== 8.18) {
        throw new Error(
          `predictCGPA prediction error. Expected 8.18, got ${cgpaPredict.predictedCGPA}`
        );
      }
    }
  ),

  // 6. AI Chat API Route Handler Query Evaluation
  registerTest(
    'AJ-06',
    'AI Chat API (/api/ai/chat)',
    'Process Attendance Query via /api/ai/chat',
    async () => {
      const req = new NextRequest('http://localhost/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: 'What is my attendance?' }],
        }),
      });

      const res = await handleAiChat(req);
      if (res.status !== 200)
        throw new Error(`Expected 200 OK from chat API, got ${res.status}`);

      const json = await res.json();
      if (!json.success || json.message?.role !== 'assistant') {
        throw new Error('Chat API returned invalid response structure');
      }
      if (!Array.isArray(json.toolCalls) || json.toolCalls.length === 0) {
        throw new Error(
          'Chat API failed to perform tool call for attendance query'
        );
      }
      if (json.toolCalls[0].tool !== 'getAttendance') {
        throw new Error(
          `Expected getAttendance tool call, got ${json.toolCalls[0].tool}`
        );
      }
    }
  ),

  // 7. AI Chat API Target Calculation Evaluation
  registerTest(
    'AJ-07',
    'AI Chat API (/api/ai/chat)',
    'Process Attendance Target Query via /api/ai/chat',
    async () => {
      const req = new NextRequest('http://localhost/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [
            {
              role: 'user',
              content: 'Calculate classes needed for 85% attendance',
            },
          ],
        }),
      });

      const res = await handleAiChat(req);
      if (res.status !== 200)
        throw new Error(`Expected 200 OK, got ${res.status}`);

      const json = await res.json();
      if (!json.success || !Array.isArray(json.toolCalls)) {
        throw new Error('Target query chat response invalid');
      }
      if (json.toolCalls[0].tool !== 'calculateAttendanceTarget') {
        throw new Error(
          `Expected calculateAttendanceTarget, got ${json.toolCalls[0].tool}`
        );
      }
    }
  ),

  // 8. AI Chat API CGPA Prediction Evaluation
  registerTest(
    'AJ-08',
    'AI Chat API (/api/ai/chat)',
    'Process CGPA Prediction Query via /api/ai/chat',
    async () => {
      const req = new NextRequest('http://localhost/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: 'Predict my CGPA' }],
        }),
      });

      const res = await handleAiChat(req);
      if (res.status !== 200)
        throw new Error(`Expected 200 OK, got ${res.status}`);

      const json = await res.json();
      if (!json.success || !Array.isArray(json.toolCalls)) {
        throw new Error('CGPA prediction chat response invalid');
      }
      if (json.toolCalls[0].tool !== 'predictCGPA') {
        throw new Error(`Expected predictCGPA, got ${json.toolCalls[0].tool}`);
      }
    }
  ),

  // 9. Error Handling & Edge Recovery
  registerTest(
    'AJ-09',
    'Error Handling & Resilience',
    'Handle Malformed Payloads & Invalid Tools Gracefully',
    async () => {
      // Malformed JSON
      const malformedReq = new NextRequest('http://localhost/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: 'invalid-json-{',
      });
      const malformedRes = await handleAiChat(malformedReq);
      if (malformedRes.status !== 400) {
        throw new Error(
          `Expected status 400 on malformed JSON, got ${malformedRes.status}`
        );
      }

      // Invalid tool execution
      const invalidToolRes = await executeTool('unregisteredTool', {});
      if (invalidToolRes.success !== false || !invalidToolRes.error) {
        throw new Error(
          'Expected executeTool to fail gracefully for unregistered tool name'
        );
      }
    }
  ),
];

async function runAgentAsJudge() {
  console.log(
    '\n================================================================================'
  );
  console.log(
    '                 🤖 KL SYNC AGENT-AS-JUDGE AI TEST SUITE                        '
  );
  console.log(
    '================================================================================\n'
  );

  let passedCount = 0;
  let failedCount = 0;
  const startTime = Date.now();

  for (const c of cases) {
    const t0 = Date.now();
    try {
      await c.fn();
      const durationMs = Date.now() - t0;
      testResults.push({
        id: c.id,
        name: c.name,
        category: c.category,
        passed: true,
        durationMs,
      });
      passedCount++;
      console.log(
        `  ✓ [${c.id}] ${c.category.padEnd(26)} : ${c.name} (${durationMs}ms)`
      );
    } catch (err: unknown) {
      const durationMs = Date.now() - t0;
      const errMsg = err instanceof Error ? err.message : String(err);
      testResults.push({
        id: c.id,
        name: c.name,
        category: c.category,
        passed: false,
        durationMs,
        error: errMsg,
      });
      failedCount++;
      console.error(
        `  ✖ [${c.id}] ${c.category.padEnd(26)} : ${c.name} (${durationMs}ms)`
      );
      console.error(`      Error: ${errMsg}`);
    }
  }

  const totalDuration = Date.now() - startTime;

  console.log(
    '\n--------------------------------------------------------------------------------'
  );
  console.log(
    `SUMMARY: ${passedCount + failedCount} Total Tests | ${passedCount} Passed | ${failedCount} Failed | Total Duration: ${totalDuration}ms`
  );
  console.log(
    '--------------------------------------------------------------------------------\n'
  );

  if (failedCount > 0) {
    console.error('💥 Agent-as-Judge suite failed! Exiting with code 1.');
    process.exit(1);
  } else {
    console.log(
      '🎉 All Agent-as-Judge capability tests passed successfully! Exiting with code 0.\n'
    );
    process.exit(0);
  }
}

runAgentAsJudge();
