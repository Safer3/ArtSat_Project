import math
E_CIRC = 1e-6
N_EQ = 1e-12
R_EARTH = 6371.0






def check_orbit(a, e_val):
    p      = a * (1.0 - e_val**2)
    r_peri = p / (1.0 + e_val)

    h_peri = r_peri - R_EARTH

    if h_peri < 0:
        #print(f"  [!] ВНИМАНИЕ: перицентр ниже радиуса Земли на {abs(h_peri):.2f} км")
        return f"  [!] ВНИМАНИЕ: перицентр ниже радиуса Земли на {abs(h_peri):.2f} км"
    else:
        orb = {
            'h_p':h_peri,
            'r_p':r_peri
        }
        if e_val < 1.0:
            r_apo = a * (1.0 + e_val)
            h_apo = r_apo - R_EARTH
            orb = {
            'h_p':h_peri,
            'r_p':r_peri,
            'h_a':h_apo,
            'r_a':r_apo
        }
        return orb
    
    


# ===============================================================
# Сценарий 1: Вектор состояния -> Элементы орбиты
# ===============================================================

def state_vector_to_elements(x = 0, y = 0, z = 0, vx = 0, vy = 0, vz = 0, mu = 398600.4418):
    
    # -- Модули r и v ------------------------------------------
    r_val = math.sqrt(x**2 + y**2 + z**2)
    v_val = math.sqrt(vx**2 + vy**2 + vz**2)

    # -- Вектор момента импульса:  h = r x v -------------------
    hx = y*vz - z*vy
    hy = z*vx - x*vz
    hz = x*vy - y*vx
    h_val = math.sqrt(hx**2 + hy**2 + hz**2)

    if h_val == 0:
        #print("\n  [!] Ошибка: момент импульса равен нулю (вырожденная орбита).")
        return "[!] Ошибка: момент импульса равен нулю (вырожденная орбита).", -1

    # -- Вектор линии узлов:  n = k x h,  k = (0, 0, 1) -------
    nx = -hy
    ny =  hx
    # nz = 0 всегда
    n_val = math.sqrt(nx**2 + ny**2)

    # -- Вектор эксцентриситета:  e = (v x h)/mu - r_hat -------
    vxh_x = vy*hz - vz*hy
    vxh_y = vz*hx - vx*hz
    vxh_z = vx*hy - vy*hx

    ex = vxh_x/mu - x/r_val
    ey = vxh_y/mu - y/r_val
    ez = vxh_z/mu - z/r_val
    e_val = math.sqrt(ex**2 + ey**2 + ez**2)

    # -- Удельная энергия:  eps = v^2/2 - mu/r -----------------
    eps = v_val**2 / 2.0 - mu / r_val
    #print(eps)

    # -- Большая полуось:  a = -mu / (2*eps) -------------------
    if abs(eps) < 1e-10:
        #print("\n  [!] Орбита параболическая (eps ≈ 0), "
              #"большая полуось не определена.")
        return "[!] Орбита параболическая (eps ≈ 0), большая полуось не определена.", -1
    a = -mu / (2.0 * eps)

    # -- Наклонение:  i = arccos(hz / h) -----------------------
    cos_i = max(-1.0, min(1.0, hz / h_val))
    i_deg = math.degrees(math.acos(cos_i))

    # -- Долгота восходящего узла:  Omega = arccos(nx / |n|) ---
    # Особый случай: экваториальная орбита (|n| ~ 0) — Omega не определена.
    if n_val < N_EQ:
        Omega = 0.0                              # соглашение
    else:
        cos_O = max(-1.0, min(1.0, nx / n_val))
        Omega = math.degrees(math.acos(cos_O))
        if ny < 0:
            Omega = 360.0 - Omega               # квадрантное условие

    # -- Аргумент перицентра:  omega = arccos((n*e) / (|n|*e)) -
    # Особые случаи:
    #   e < E_CIRC  -- круговая орбита, omega не определён -> 0 по соглашению
    #   |n| < N_EQ  -- экваториальная орбита, omega отсчитывается от оси X
    if e_val < E_CIRC:
        omega = 0.0                              # соглашение для круговой
    elif n_val < N_EQ:
        cos_w = max(-1.0, min(1.0, ex / e_val))
        omega = math.degrees(math.acos(cos_w))
        if ez < 0:
            omega = 360.0 - omega               # квадрантное условие
    else:
        n_dot_e = nx*ex + ny*ey                  # nz = 0
        cos_w = max(-1.0, min(1.0, n_dot_e / (n_val * e_val)))
        omega = math.degrees(math.acos(cos_w))
        if ez < 0:
            omega = 360.0 - omega               # квадрантное условие

    # -- Истинная аномалия nu -----------------------------------
    # Особые случаи:
    #   e < E_CIRC  -- круговая орбита, nu отсчитывается от линии узлов (или от X)
    #   e >= E_CIRC -- стандартная формула через вектор эксцентриситета
    if e_val < E_CIRC:
        if n_val < N_EQ:
            # Круговая экваториальная: nu от оси X
            cos_nu = x / r_val
            sin_nu = y / r_val
        else:
            # Круговая наклонённая: nu — угол от линии узлов.
            #   cos(nu) = r_hat * n_hat
            #   sin(nu) = r_hat * (h_hat x n_hat)
            # Формула через (h_hat x n_hat) корректна при любом наклонении,
            # в том числе при i = 90° (hz = 0), когда альтернативная формула
            # hz*(n x v) тождественно обнуляется и не позволяет определить квадрант.
            nx_u = nx / n_val
            ny_u = ny / n_val
            hx_u = hx / h_val
            hy_u = hy / h_val
            hz_u = hz / h_val
            # h_hat x n_hat  (nz = 0 всегда, поэтому два члена обнуляются)
            q_x = hy_u * 0.0 - hz_u * ny_u
            q_y = hz_u * nx_u - hx_u * 0.0
            q_z = hx_u * ny_u - hy_u * nx_u
            cos_nu = (nx_u * x + ny_u * y) / r_val
            sin_nu = (q_x * x + q_y * y + q_z * z) / r_val
        nu = math.degrees(math.atan2(sin_nu, cos_nu)) % 360.0
    else:
        # Эллиптическая/гиперболическая орбита
        cos_nu = max(-1.0, min(1.0, (ex*x + ey*y + ez*z) / (e_val * r_val)))
        nu = math.degrees(math.acos(cos_nu))
        if x*vx + y*vy + z*vz < 0:
            nu = 360.0 - nu                     # квадрантное условие

    data_to_import = {
        'a':a,
        'e_val':e_val,
        'i_deg':i_deg,
        "O_deg":Omega,
        "w_deg":omega,
        'nu_deg':nu,
      

    }


    orb = check_orbit(a, e_val)
    #if a != 0:
    #    return a
    #else:
    return data_to_import, orb



    #print(data_to_import)
    # print()
    # print(f"  Большая полуось                       a  = {a:.6g}")
    # print(f"  Эксцентриситет                        e  = {e_val:.6g}")
    # print(f"  Наклонение                            i  = {i_deg:.6f}\u00b0")
    # print(f"  Долгота восходящего узла              \u03a9  = {Omega:.6f}\u00b0")
    # print(f"  Аргумент перицентра                   \u03c9  = {omega:.6f}\u00b0")
    # print(f"  Истинная аномалия                     \u03bd  = {nu:.6f}\u00b0")
    # print()
    # print("  (Вспомогательные величины)")
    # print(f"  Модуль радиус-вектора                 r  = {r_val:.6g}")
    # print(f"  Модуль вектора скорости               v  = {v_val:.6g}")
    # print(f"  Модуль момента импульса               h  = {h_val:.6g}")
    # print(f"  Удельная энергия                      \u03b5  = {eps:.6g}")

  

# ===============================================================
# Сценарий 2: Элементы орбиты -> Вектор состояния
# ===============================================================

def elements_to_state_vector(a = 0, e_val = 0, i_deg = 0, O_deg = 0, w_deg = 0, nu_deg = 0, mu = 398600.4418):

    i  = math.radians(i_deg)
    O  = math.radians(O_deg)
    w  = math.radians(w_deg)
    nu = math.radians(nu_deg)

    # -- Фокальный параметр:  p = a(1 - e^2) ------------------
    p = a * (1.0 - e_val**2)

    # -- Радиус орбиты:  r = p / (1 + e*cos(nu)) --------------
    r_val = p / (1.0 + e_val * math.cos(nu))

    # -- Радиус-вектор и скорость в орбитальной СК -------------
    r_orb = [r_val * math.cos(nu),
             r_val * math.sin(nu),
             0.0]

    sqrt_mu_p = math.sqrt(mu / p)
    v_orb = [-sqrt_mu_p * math.sin(nu),
              sqrt_mu_p * (e_val + math.cos(nu)),
              0.0]

    # -- Матрица поворота:  Q = Rz(Omega) * Rx(i) * Rz(omega) -
    cO, sO = math.cos(O), math.sin(O)
    ci, si = math.cos(i), math.sin(i)
    cw, sw = math.cos(w), math.sin(w)

    Q = [
        [ cO*cw - sO*sw*ci,  -cO*sw - sO*cw*ci,  sO*si ],
        [ sO*cw + cO*sw*ci,  -sO*sw + cO*cw*ci, -cO*si ],
        [ sw*si,               cw*si,              ci   ],
    ]

    def mat_vec(M, vec):
        return [sum(M[row][col] * vec[col] for col in range(3))
                for row in range(3)]

    # -- Переход в инерциальную СК -----------------------------
    r_eci = mat_vec(Q, r_orb)
    v_eci = mat_vec(Q, v_orb)

    r_mod = math.sqrt(sum(c**2 for c in r_eci))
    v_mod = math.sqrt(sum(c**2 for c in v_eci))

    data_to_import = {
        'x':r_eci[0],
        'y':r_eci[1],
        'z':r_eci[2],
        "vx":v_eci[0],
        "vy":v_eci[1],
        'vz':v_eci[2],
     

    }

    orb = check_orbit(a, e_val)

    # a = check_orbit(a, e_val)
    # if a != 0:
    #     return a
    # else:
    return data_to_import, orb


    
    # print()
    # print(f"  Радиус-вектор:")
    # print(f"    x  = {r_eci[0]:.6g}")
    # print(f"    y  = {r_eci[1]:.6g}")
    # print(f"    z  = {r_eci[2]:.6g}")
    # print()
    # print(f"  Вектор скорости:")
    # print(f"    vx = {v_eci[0]:.6g}")
    # print(f"    vy = {v_eci[1]:.6g}")
    # print(f"    vz = {v_eci[2]:.6g}")
    # print()
    # print("  (Вспомогательные величины)")
    # r_mod = math.sqrt(sum(c**2 for c in r_eci))
    # v_mod = math.sqrt(sum(c**2 for c in v_eci))
    # print(f"  Модуль радиус-вектора   r = {r_mod:.6g}")
    # print(f"  Модуль вектора скорости v = {v_mod:.6g}")







    # else:
    #     print(f"  [+] Орбита над поверхностью Земли.")
    #     print(f"      Высота перицентра:       h_пери = {h_peri:.2f} км")
    #     print(f"      Перицентрное расстояние: r_пери = {r_peri:.2f} км")
    #     if e_val < 1.0:
    #         r_apo = a * (1.0 + e_val)
    #         h_apo = r_apo - R_EARTH
    #         print(f"      Высота апоцентра:        h_апо  = {h_apo:.2f} км")
    #         print(f"      Апоцентрное расстояние:  r_апо  = {r_apo:.2f} км")




