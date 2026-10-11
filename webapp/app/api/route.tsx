
import { NextResponse } from "next/server";

export const GET = (req: Request) => {
    console.log(req);
    // console.log(res);
    return NextResponse.json({ 'status': 'OK' }, {
        status: 200
    });
}
