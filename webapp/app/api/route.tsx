
import { NextResponse } from "next/server";

export const GET = (req: Request) => {
    return NextResponse.json({ 'status': 'OK' }, {
        status: 200
    });
}
