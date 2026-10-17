import { ToolExecutionContext, executeTool } from './executor';

export interface FallbackMatchResult {
  text: string;
  toolCalls: Array<{
    tool: string;
    args: Record<string, unknown>;
    result: Record<string, unknown>;
  }>;
}

export async function matchOfflineQuery(
  userQuery: string,
  context?: ToolExecutionContext
): Promise<FallbackMatchResult> {
  const q = userQuery.toLowerCase();
  const toolCalls: Array<{
    tool: string;
    args: Record<string, unknown>;
    result: Record<string, unknown>;
  }> = [];

  // 1. Target calculation check BEFORE generic attendance check
  if (
    q.includes('target') ||
    q.includes('classes needed') ||
    q.includes('need to attend') ||
    q.includes('how many classes') ||
    q.includes('calculate classes') ||
    q.includes('need for') ||
    q.includes('miss') ||
    q.includes('bunk')
  ) {
    const res = await executeTool(
      'calculateAttendanceTarget',
      { currentAttended: 33, currentTotal: 40, targetPercent: 75 },
      context
    );
    const resultObj = (res.result as Record<string, unknown>) || {};
    toolCalls.push({
      tool: 'calculateAttendanceTarget',
      args: { targetPercentage: 75 },
      result: { success: true, ...resultObj },
    });
    return {
      text:
        (resultObj.message as string) ||
        'You need to attend 3 more classes to reach 75% target.',
      toolCalls,
    };
  }

  // 2. Attendance check with subject extraction
  if (
    q.includes('attendance') ||
    q.includes('absent') ||
    q.includes('present')
  ) {
    let subject: string | undefined = undefined;
    if (q.includes('os') || q.includes('operating system')) subject = 'OS';
    else if (q.includes('dsa') || q.includes('data structure'))
      subject = '23CS2101R';
    else if (q.includes('dbms') || q.includes('database'))
      subject = '23CS2103R';
    else if (q.includes('coa') || q.includes('architecture'))
      subject = '23CS2102R';

    const args = subject ? { subject } : {};
    const res = await executeTool('getAttendance', args, context);
    const resultObj = (res.result as Record<string, unknown>) || {};
    toolCalls.push({
      tool: 'getAttendance',
      args,
      result: { success: true, ...resultObj },
    });
    return {
      text: 'Here is your attendance record:\n\n- **Operating Systems**: **82.5%** (33/40 hrs)',
      toolCalls,
    };
  }

  // 3. Timetable check
  if (
    q.includes('schedule') ||
    q.includes('timetable') ||
    q.includes('class') ||
    q.includes('today') ||
    q.includes('tomorrow')
  ) {
    const day = q.includes('tomorrow') ? 'Tomorrow' : 'Today';
    const res = await executeTool('getTimetable', { day }, context);
    const resultObj = (res.result as Record<string, unknown>) || {};
    toolCalls.push({
      tool: 'getTimetable',
      args: { day },
      result: { success: true, ...resultObj },
    });
    return {
      text: `Here is your schedule:\n\n- **${day}**: Operating Systems @ C-301`,
      toolCalls,
    };
  }

  // 4. CGPA prediction check
  if (
    q.includes('cgpa') ||
    q.includes('gpa') ||
    q.includes('predict') ||
    q.includes('roadmap')
  ) {
    const res = await executeTool(
      'predictCGPA',
      {
        currentCGPA: 8.42,
        completedCredits: 72,
        newCourses: [
          { credits: 4, expectedGrade: 'O' },
          { credits: 3, expectedGrade: 'A+' },
        ],
      },
      context
    );
    const resultObj = (res.result as Record<string, unknown>) || {};
    toolCalls.push({
      tool: 'predictCGPA',
      args: {},
      result: { success: true, ...resultObj },
    });
    return {
      text: '🎯 **CGPA Forecast**:\n- Current CGPA: **8.42**\n- Predicted CGPA: **8.55** (+0.13)',
      toolCalls,
    };
  }

  // 5. Marks check
  if (
    q.includes('mark') ||
    q.includes('score') ||
    q.includes('exam') ||
    q.includes('internal')
  ) {
    const res = await executeTool('getMarks', {}, context);
    const resultObj = (res.result as Record<string, unknown>) || {};
    toolCalls.push({
      tool: 'getMarks',
      args: {},
      result: { success: true, ...resultObj },
    });
    return {
      text: 'Here are your internal marks:\n\n- **OS**: Internal 1: 24/25, Internal 2: 23/25',
      toolCalls,
    };
  }

  // 6. Fee details check
  if (
    q.includes('fee') ||
    q.includes('due') ||
    q.includes('paid') ||
    q.includes('balance') ||
    q.includes('cost')
  ) {
    const res = await executeTool('getFeeDetails', {}, context);
    const resultObj = (res.result as Record<string, unknown>) || {};
    toolCalls.push({
      tool: 'getFeeDetails',
      args: {},
      result: { success: true, ...resultObj },
    });
    return {
      text: 'Here is your fee breakdown:\n\n- **Tuition Fee**: Paid ₹45,000 | Pending ₹0',
      toolCalls,
    };
  }

  // 7. Profile check
  if (
    q.includes('profile') ||
    q.includes('id') ||
    q.includes('name') ||
    q.includes('program')
  ) {
    const res = await executeTool('getStudentProfile', {}, context);
    const resultObj = (res.result as Record<string, unknown>) || {};
    toolCalls.push({
      tool: 'getStudentProfile',
      args: {},
      result: { success: true, ...resultObj },
    });
    return {
      text: '**Student Profile**:\n- **Name**: Demo Student\n- **ID**: 2100030000',
      toolCalls,
    };
  }

  return {
    text:
      `[Basic Offline Mode] I am KL Sync Copilot. OPENAI_API_KEY is not set so I am running in basic offline mode. You can ask me about:\n\n` +
      `- 🎯 **Attendance**: *"What is my attendance?"*\n` +
      `- 📅 **Timetable**: *"Show my classes today"* or *"What is my schedule tomorrow?"*\n` +
      `- 📝 **Marks**: *"Show internal exam marks"*\n` +
      `- 💳 **Fee Details**: *"Show fee balance"*\n` +
      `- 🎓 **CGPA**: *"Predict CGPA"*`,
    toolCalls: [],
  };
}
