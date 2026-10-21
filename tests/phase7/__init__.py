"""Phase 7 — the transient scenario runner: V1 and the rewrite on one operating procedure.

What this is
------------
The validation phase's driver (handoff A-14: "the Phase 7 driver runs V1 at the same step"). A
scenario is an operating procedure — an initial condition, a timed list of the operator's and the
instructor's commands, a disturbance — and the packet paths a comparison reads. The runner drives
V1's own ``step_sim`` and the rewrite's scheduler through it, each in its own process, both at the
engine's fixed 0.1 s step; the commands reach V1 through its ``handle_cmd`` and the rewrite through
``engine.command.apply_command``, between two ticks, as an operator's would. Both publish the
console packet on V1's key paths, so one path reads the same quantity on both sides.

    scenarios   the procedures: cold start, trip 22.2, HPCC rupture, vacuum break
    drivers     one side through a procedure, sampled, every tick watched for ringing (B-51)
    compare     the two sides' records side by side, the ringing and the cold start's FOPTD
    run         the command line: ``python -m tests.phase7.run <scenario> [--side ...]``
    deviations  the process-deviation notes of `References/scenarios`, each claim put on the
                port's plant on the console's own lever (As-Built Part LXXV)
    run_deviations  the command line for them: ``python -m tests.phase7.run_deviations OUT_DIR``

Nothing here is the product: it is the validation harness, like `tests/equivalence`, and it reads
V1's source tree, which it never writes (V1 restores its design pin from its own cache; the driver
reports it if V1 had to rebuild it). As-Built Part LXII.4.
"""
