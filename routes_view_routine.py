from flask import render_template, redirect, url_for, session
from db import get_db_connection, WEEK_DAYS

def init_view_routine_routes(app):
    @app.route("/view-routine")
    def view_routine():
        if "routine_table" not in session:
            return redirect(url_for("select_details"))

        routine_table = session["routine_table"]

        conn = get_db_connection()
        cur = conn.cursor()

        # Get time slots for headers
        cur.execute(f"""
            SELECT DISTINCT slot_start, slot_end 
            FROM {routine_table} 
            ORDER BY slot_start
        """)
        slots = cur.fetchall()
        slot_labels = [f"{s[0].strftime('%H:%M')} - {s[1].strftime('%H:%M')}" for s in slots]

        # Get days in order
        start_day = session.get("start_day", "Monday")
        end_day = session.get("end_day", "Friday")
        s_idx = WEEK_DAYS.index(start_day)
        e_idx = WEEK_DAYS.index(end_day)
        days_range = WEEK_DAYS[s_idx:e_idx+1] if s_idx <= e_idx else WEEK_DAYS[s_idx:] + WEEK_DAYS[:e_idx+1]

        # Get all routine data
        cur.execute(f"""
            SELECT day, slot_start, slot_end, teacher_name, course_code, is_lab, classroom
            FROM {routine_table}
            ORDER BY day, slot_start
        """)
        rows = cur.fetchall()

        # Organize data for display
        routine = {}
        for day in days_range:
            routine[day] = {}
            for slot in slot_labels:
                routine[day][slot] = "Free"

        for day, start, end, teacher, code, is_lab, classroom in rows:
            slot_label = f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}"
            if teacher:
                display_text = f"{teacher}\n{code}"
                if is_lab:
                    display_text += " (Lab)"
                if classroom:
                    display_text += f"\nRoom: {classroom}"
                routine[day][slot_label] = display_text
            elif routine[day][slot_label] == "Free":
                # Check if this is a break slot
                cur.execute(f"""
                    SELECT 1 FROM {routine_table}
                    WHERE day = %s AND slot_start = %s AND time_slot = 'BREAK'
                """, (day, start))
                if cur.fetchone():
                    routine[day][slot_label] = "Break"

        # Prepare table rows
        table_rows = []
        for day in days_range:
            row = [day] + [routine[day][slot] for slot in slot_labels]
            table_rows.append(row)

        cur.close()
        conn.close()

        return render_template(
            "view_routine.html",
            slot_labels=slot_labels,
            table_rows=table_rows,
            branch=session.get("branch"),
            semester=session.get("semester"),
            year=session.get("year")
        )