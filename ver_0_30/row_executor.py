import time

def execute_row(
    builder,
    row_tasks,
    column_task_cls,
    aux_z_offset=1,
    sleep_between_columns=0.3,
    row_idx=0,
    progress_manager=None,
    structure_hash=None,
    relative_structure_hash=None,
    stop_controller=None,
    resume_state=None,
    resume_player_pos=None,
):
    """
    执行单行任务，支持：
    - 中断恢复
    - 热键停止
    - 辅助柱阶段恢复
    """

    if not row_tasks:
        print("[execute_row] row_tasks 为空，跳过")
        return True, {
            "real_column_count": 0,
            "aux_actual_top": 0,
            "last_real_actual_top": 0,
            "stopped": False,
            "phase": "done",
            "next_col_idx": 0,
        }

    if resume_state is None:
        resume_state = {}

    phase = resume_state.get("phase", "real_columns")
    next_col_idx = int(resume_state.get("next_col_idx", 0))
    prev_column_y_values = resume_state.get("prev_column_y_values", None)
    prev_actual_top = int(resume_state.get("prev_actual_top", 0))
    aux_actual_top = int(resume_state.get("aux_actual_top", 0))

    print(
        f"\n[execute_row] ==== row_idx={row_idx}, phase={phase}, "
        f"next_col_idx={next_col_idx} ===="
    )

    def save_progress(
        phase_value,
        next_col_idx_value,
        prev_column_y_values_value,
        prev_actual_top_value,
        aux_actual_top_value,
    ):
        if progress_manager is not None and structure_hash is not None:
            progress_manager.save_row_resume(
                structure_hash=structure_hash,
                relative_structure_hash=relative_structure_hash,
                row_idx=row_idx,
                next_col_idx=next_col_idx_value,
                phase=phase_value,
                prev_actual_top=prev_actual_top_value,
                prev_column_y_values=prev_column_y_values_value,
                aux_actual_top=aux_actual_top_value,
                resume_player_pos=resume_player_pos,
            )

    # =========================
    # 阶段1：真实柱
    # =========================
    if phase == "real_columns":
        print("\n[execute_row] ==== start real columns ====")

        for col_idx in range(next_col_idx, len(row_tasks)):
            if stop_controller is not None and stop_controller.should_stop():
                print(f"[execute_row] stop before real column {col_idx + 1}/{len(row_tasks)}")
                save_progress(
                    phase_value="real_columns",
                    next_col_idx_value=col_idx,
                    prev_column_y_values_value=prev_column_y_values,
                    prev_actual_top_value=prev_actual_top,
                    aux_actual_top_value=0,
                )
                return False, {
                    "real_column_count": col_idx,
                    "aux_actual_top": 0,
                    "last_real_actual_top": prev_actual_top,
                    "stopped": True,
                    "phase": "real_columns",
                    "next_col_idx": col_idx,
                }

            task = row_tasks[col_idx]
            print(f"[execute_row] build real column {col_idx + 1}/{len(row_tasks)}: {task}")

            ok, actual_top = builder.build_column(
                task,
                prev_column_y_values=prev_column_y_values,
                prev_actual_top=prev_actual_top,
            )
            if not ok:
                print("[execute_row] build real column failed")
                save_progress(
                    phase_value="real_columns",
                    next_col_idx_value=col_idx,
                    prev_column_y_values_value=prev_column_y_values,
                    prev_actual_top_value=prev_actual_top,
                    aux_actual_top_value=0,
                )
                return False, {
                    "real_column_count": col_idx,
                    "aux_actual_top": 0,
                    "last_real_actual_top": prev_actual_top,
                    "stopped": False,
                    "phase": "real_columns",
                    "next_col_idx": col_idx,
                }

            prev_column_y_values = (
                list(task.y_values) if getattr(task, "y_values", None) is not None else None
            )
            prev_actual_top = actual_top

            save_progress(
                phase_value="real_columns",
                next_col_idx_value=col_idx + 1,
                prev_column_y_values_value=prev_column_y_values,
                prev_actual_top_value=prev_actual_top,
                aux_actual_top_value=0,
            )

            if stop_controller is not None and stop_controller.should_stop():
                print(f"[execute_row] stop after real column {col_idx + 1}/{len(row_tasks)}")
                return False, {
                    "real_column_count": col_idx + 1,
                    "aux_actual_top": 0,
                    "last_real_actual_top": prev_actual_top,
                    "stopped": True,
                    "phase": "real_columns",
                    "next_col_idx": col_idx + 1,
                }

            if sleep_between_columns > 0:
                time.sleep(sleep_between_columns)

        phase = "aux_build"

    # =========================
    # 阶段2：建辅助柱
    # =========================
    if phase == "aux_build":
        if stop_controller is not None and stop_controller.should_stop():
            print("[execute_row] stop before building auxiliary column")
            save_progress(
                phase_value="aux_build",
                next_col_idx_value=len(row_tasks),
                prev_column_y_values_value=prev_column_y_values,
                prev_actual_top_value=prev_actual_top,
                aux_actual_top_value=0,
            )
            return False, {
                "real_column_count": len(row_tasks),
                "aux_actual_top": 0,
                "last_real_actual_top": prev_actual_top,
                "stopped": True,
                "phase": "aux_build",
                "next_col_idx": len(row_tasks),
            }

        print("\n[execute_row] ==== build auxiliary column ====")

        last = row_tasks[-1]
        aux_task = column_task_cls(
            x=last.x,
            z=last.z + aux_z_offset,
            w=last.w,
            y_values=[],
            is_auxiliary=True,
        )

        print(f"[execute_row] build aux column: {aux_task}")

        ok, aux_actual_top = builder.build_column(
            aux_task,
            prev_column_y_values=prev_column_y_values,
            prev_actual_top=prev_actual_top,
        )
        if not ok:
            print("[execute_row] build auxiliary column failed")
            save_progress(
                phase_value="aux_build",
                next_col_idx_value=len(row_tasks),
                prev_column_y_values_value=prev_column_y_values,
                prev_actual_top_value=prev_actual_top,
                aux_actual_top_value=0,
            )
            return False, {
                "real_column_count": len(row_tasks),
                "aux_actual_top": 0,
                "last_real_actual_top": prev_actual_top,
                "stopped": False,
                "phase": "aux_build",
                "next_col_idx": len(row_tasks),
            }

        save_progress(
            phase_value="aux_break",
            next_col_idx_value=len(row_tasks),
            prev_column_y_values_value=prev_column_y_values,
            prev_actual_top_value=prev_actual_top,
            aux_actual_top_value=aux_actual_top,
        )

        if stop_controller is not None and stop_controller.should_stop():
            print("[execute_row] stop after building auxiliary column")
            return False, {
                "real_column_count": len(row_tasks),
                "aux_actual_top": aux_actual_top,
                "last_real_actual_top": prev_actual_top,
                "stopped": True,
                "phase": "aux_break",
                "next_col_idx": len(row_tasks),
            }

        if sleep_between_columns > 0:
            time.sleep(sleep_between_columns)

        phase = "aux_break"

    # =========================
    # 阶段3：拆辅助柱
    # =========================
    if phase == "aux_break":
        if stop_controller is not None and stop_controller.should_stop():
            print("[execute_row] stop before breaking auxiliary column")
            save_progress(
                phase_value="aux_break",
                next_col_idx_value=len(row_tasks),
                prev_column_y_values_value=prev_column_y_values,
                prev_actual_top_value=prev_actual_top,
                aux_actual_top_value=aux_actual_top,
            )
            return False, {
                "real_column_count": len(row_tasks),
                "aux_actual_top": aux_actual_top,
                "last_real_actual_top": prev_actual_top,
                "stopped": True,
                "phase": "aux_break",
                "next_col_idx": len(row_tasks),
            }

        print("\n[execute_row] ==== break auxiliary column ====")

        ok = builder.break_whole_column(aux_actual_top)
        if not ok:
            print("[execute_row] break auxiliary column failed")
            save_progress(
                phase_value="aux_break",
                next_col_idx_value=len(row_tasks),
                prev_column_y_values_value=prev_column_y_values,
                prev_actual_top_value=prev_actual_top,
                aux_actual_top_value=aux_actual_top,
            )
            return False, {
                "real_column_count": len(row_tasks),
                "aux_actual_top": aux_actual_top,
                "last_real_actual_top": prev_actual_top,
                "stopped": False,
                "phase": "aux_break",
                "next_col_idx": len(row_tasks),
            }

    print("[execute_row] ==== row done ====")

    return True, {
        "real_column_count": len(row_tasks),
        "aux_actual_top": aux_actual_top,
        "last_real_actual_top": prev_actual_top,
        "stopped": False,
        "phase": "done",
        "next_col_idx": len(row_tasks),
    }

def execute_rows(
    builder,
    rows,
    column_task_cls,
    aux_z_offset=1,
    sleep_between_rows=0.5,
    sleep_between_columns=0.3,
    progress_manager=None,
    structure_hash=None,
    relative_structure_hash=None,
    stop_controller=None,
    resume_info=None,
    resume_player_pos=None,
):
    """
    执行多行任务，支持恢复。
    """

    if not rows:
        print("[execute_rows] rows 为空")
        return True, {
            "all_results": [],
            "stopped": False,
            "resume_row_idx": None,
        }

    all_results = []
    start_row_idx = 0
    start_resume_state = None

    if resume_info is not None:
        start_row_idx = int(resume_info.get("row_idx", 0))
        start_resume_state = {
            "phase": resume_info.get("phase", "real_columns"),
            "next_col_idx": int(resume_info.get("next_col_idx", 0)),
            "prev_column_y_values": resume_info.get("prev_column_y_values", None),
            "prev_actual_top": int(resume_info.get("prev_actual_top", 0)),
            "aux_actual_top": int(resume_info.get("aux_actual_top", 0)),
        }
        print(f"[execute_rows] resume from row_idx={start_row_idx}, state={start_resume_state}")

    print("\n[execute_rows] ==== start all rows ====")

    for row_idx in range(start_row_idx, len(rows)):
        row_tasks = rows[row_idx]
        print(f"\n[execute_rows] ==== row {row_idx + 1}/{len(rows)} ====")

        resume_state = start_resume_state if row_idx == start_row_idx else None

        ok, row_result = execute_row(
            builder=builder,
            row_tasks=row_tasks,
            column_task_cls=column_task_cls,
            aux_z_offset=aux_z_offset,
            sleep_between_columns=sleep_between_columns,
            row_idx=row_idx,
            progress_manager=progress_manager,
            structure_hash=structure_hash,
            relative_structure_hash=relative_structure_hash,
            stop_controller=stop_controller,
            resume_state=resume_state,
            resume_player_pos=resume_player_pos,
        )

        all_results.append(row_result)

        if not ok:
            print(f"[execute_rows] row {row_idx + 1} failed or stopped")
            return False, {
                "all_results": all_results,
                "stopped": bool(row_result.get("stopped", False)),
                "resume_row_idx": row_idx,
            }

        if progress_manager is not None and structure_hash is not None:
            progress_manager.save_row_resume(
                structure_hash=structure_hash,
                relative_structure_hash=relative_structure_hash,
                row_idx=row_idx + 1,
                next_col_idx=0,
                phase="real_columns",
                prev_actual_top=0,
                prev_column_y_values=None,
                aux_actual_top=0,
                resume_player_pos=resume_player_pos,
            )

        if stop_controller is not None and stop_controller.should_stop():
            print(f"[execute_rows] stop after row {row_idx + 1}")
            return False, {
                "all_results": all_results,
                "stopped": True,
                "resume_row_idx": row_idx + 1,
            }

        if sleep_between_rows > 0 and row_idx < len(rows) - 1:
            time.sleep(sleep_between_rows)

    print("\n[execute_rows] ==== all rows done ====")
    return True, {
        "all_results": all_results,
        "stopped": False,
        "resume_row_idx": None,
    }
