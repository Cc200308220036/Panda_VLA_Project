import os
import mujoco


def main():
    xml_path = os.path.expanduser(
        "~/panda_vla_project/mujoco_env/assets/robots/franka_panda/panda_pick_place.xml"
    )

    model = mujoco.MjModel.from_xml_path(xml_path)

    print("=" * 80)
    print("Basic model info")
    print("nq:", model.nq)
    print("nv:", model.nv)
    print("nu:", model.nu)
    print("nbody:", model.nbody)
    print("njnt:", model.njnt)
    print("ngeom:", model.ngeom)
    print("=" * 80)

    print("\nJoints:")
    for i in range(model.njnt):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i)
        qadr = int(model.jnt_qposadr[i])
        dadr = int(model.jnt_dofadr[i])
        print(f"{i:02d}  name={name:25s} qposadr={qadr:2d} dofadr={dadr:2d}")

    print("\nBodies:")
    for i in range(model.nbody):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, i)
        print(f"{i:02d}  name={name}")

    print("\nActuators:")
    for i in range(model.nu):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
        ctrlrange = model.actuator_ctrlrange[i]
        trntype = model.actuator_trntype[i]
        print(
            f"{i:02d}  name={name:25s} "
            f"ctrlrange=[{ctrlrange[0]:.3f}, {ctrlrange[1]:.3f}] "
            f"trntype={trntype}"
        )


if __name__ == "__main__":
    main()
