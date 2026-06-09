import { NextResponse } from 'next/server';

// don't cache the results
export const revalidate = 0;

export async function POST() {
  return NextResponse.json(
    {
      error:
        'Phase 0 setup does not expose LiveKit token generation yet. Implement the token flow in Phase 1.',
    },
    { status: 501, headers: { 'Cache-Control': 'no-store' } }
  );
}
