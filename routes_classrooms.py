from flask import render_template, request, redirect, url_for, session
from db import get_db_connection
import random

def init_classroom_routes(app):

    def assign_classrooms_for_multi_sessions(cur, routine_table, tutorial_rooms, lab_rooms):
        """Assign classrooms for multi-slot sessions."""
        cur.execute(f"""
            WITH session_groups AS (
                SELECT 
                    day, 
                    teacher_name, 
                    course_code, 
                    is_lab,
                    slot_start,
                    LEAD(slot_start) OVER (PARTITION BY day ORDER BY slot_start) as next_slot,
                    COUNT(*) OVER (PARTITION BY day, teacher_name, course_code, grp) as session_count
                FROM (
                    SELECT *,
                    SUM(CASE WHEN teacher_name IS NULL OR time_slot = 'BREAK' THEN 1 ELSE 0 END) 
                        OVER (PARTITION BY day ORDER BY slot_start) as grp
                    FROM {routine_table}
                ) t
                WHERE teacher_name IS NOT NULL
            )
            SELECT day, MIN(slot_start) as start_time, MAX(next_slot) as end_time, 
                   teacher_name, course_code, is_lab, session_count
            FROM session_groups
            WHERE session_count > 1
            GROUP BY day, teacher_name, course_code, is_lab, session_count
            ORDER BY random()
        """)
        multi_sessions = cur.fetchall()

        for day, start, end, teacher, code, is_lab, count in multi_sessions:
            rooms = lab_rooms if is_lab else tutorial_rooms
            room = random.choice(rooms)
            cur.execute(f"""
                UPDATE {routine_table}
                SET classroom = %s
                WHERE day = %s
                AND slot_start >= %s
                AND slot_end <= %s
                AND teacher_name = %s
                AND course_code = %s
            """, (room, day, start, end, teacher, code))

    def assign_classrooms_for_single_sessions(cur, routine_table, tutorial_rooms, lab_rooms):
        """Assign classrooms for single-slot sessions."""
        cur.execute(f"""
            SELECT day, slot_start, slot_end, teacher_name, course_code, is_lab
            FROM {routine_table}
            WHERE teacher_name IS NOT NULL
            AND time_slot != 'BREAK'
            AND classroom IS NULL
            ORDER BY random()
        """)
        single_sessions = cur.fetchall()

        for i, (day, start, end, teacher, code, is_lab) in enumerate(single_sessions):
            rooms = lab_rooms if is_lab else tutorial_rooms
            room = rooms[i % len(rooms)]
            cur.execute(f"""
                UPDATE {routine_table}
                SET classroom = %s
                WHERE day = %s
                AND slot_start = %s
                AND slot_end = %s
                AND teacher_name = %s
                AND course_code = %s
            """, (room, day, start, end, teacher, code))

    @app.route("/classroom-assignment", methods=["GET", "POST"])
    def classroom_assignment():
        if "routine_table" not in session:
            return redirect(url_for("select_details"))

        if request.method == "POST":
            tutorial_rooms = [room.strip() for room in request.form["tutorial_rooms"].split(",") if room.strip()]
            lab_rooms = [room.strip() for room in request.form["lab_rooms"].split(",") if room.strip()]

            if not tutorial_rooms or not lab_rooms:
                return render_template("classroom_assignment.html", 
                                    error="Please provide at least one classroom for each type")

            session["tutorial_rooms"] = tutorial_rooms
            session["lab_rooms"] = lab_rooms

            conn = get_db_connection()
            cur = conn.cursor()
            routine_table = session["routine_table"]

            # Clear any existing classroom assignments
            cur.execute(f"""
                UPDATE {routine_table}
                SET classroom = NULL
                WHERE teacher_name IS NOT NULL
            """)

            # Assign classrooms to multi-slot sessions first
            assign_classrooms_for_multi_sessions(cur, routine_table, tutorial_rooms, lab_rooms)
            
            # Then assign to single-slot sessions
            assign_classrooms_for_single_sessions(cur, routine_table, tutorial_rooms, lab_rooms)

            conn.commit()
            cur.close()
            conn.close()

            return redirect(url_for("view_routine"))

        return render_template("classroom_assignment.html")