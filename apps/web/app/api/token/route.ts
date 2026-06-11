import { NextResponse } from 'next/server';

// don't cache the results
export const revalidate = 0;

export async function POST() {
  return NextResponse.json(
    {
      error:
        'This local route is not used in the current setup. Start the API service and request the session there instead.',
    },
    { status: 501, headers: { 'Cache-Control': 'no-store' } }
  );
}
