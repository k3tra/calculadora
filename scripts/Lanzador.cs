// Lanzador: ejecuta scripts\iniciar.ps1 del proyecto en esta misma ventana de consola.
// Compilar: scripts\crear-exe.ps1 (usa el csc.exe que trae Windows; no hace falta instalar nada).
// Los procesos van dentro de un "job" de Windows con KILL_ON_JOB_CLOSE: si el lanzador termina por
// cualquier motivo (cerrar la ventana, matarlo desde el Administrador de tareas) Windows mata todo el arbol
// (powershell, uvicorn, node), sin depender de que el script llegue a ejecutar su limpieza.
using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;

class Lanzador
{
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    static extern IntPtr CreateJobObject(IntPtr atributos, string nombre);

    [DllImport("kernel32.dll")]
    static extern bool SetInformationJobObject(IntPtr job, int clase, IntPtr info, uint tamano);

    [DllImport("kernel32.dll")]
    static extern bool AssignProcessToJobObject(IntPtr job, IntPtr proceso);

    [StructLayout(LayoutKind.Sequential)]
    struct BasicLimits
    {
        public long PerProcessUserTimeLimit, PerJobUserTimeLimit;
        public uint LimitFlags;
        public UIntPtr MinimumWorkingSetSize, MaximumWorkingSetSize;
        public uint ActiveProcessLimit;
        public UIntPtr Affinity;
        public uint PriorityClass, SchedulingClass;
    }

    [StructLayout(LayoutKind.Sequential)]
    struct IoCounters
    {
        public ulong a, b, c, d, e, f;
    }

    [StructLayout(LayoutKind.Sequential)]
    struct ExtendedLimits
    {
        public BasicLimits Basic;
        public IoCounters Io;
        public UIntPtr ProcessMemoryLimit, JobMemoryLimit, PeakProcessMemoryUsed, PeakJobMemoryUsed;
    }

    static IntPtr CrearJobQueMataAlCerrar()
    {
        IntPtr job = CreateJobObject(IntPtr.Zero, null);
        var info = new ExtendedLimits();
        info.Basic.LimitFlags = 0x2000; // JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        int tamano = Marshal.SizeOf(typeof(ExtendedLimits));
        IntPtr ptr = Marshal.AllocHGlobal(tamano);
        Marshal.StructureToPtr(info, ptr, false);
        SetInformationJobObject(job, 9, ptr, (uint)tamano); // JobObjectExtendedLimitInformation
        Marshal.FreeHGlobal(ptr);
        return job;
    }

    static int Main(string[] args)
    {
        // El .exe se copia al Escritorio, asi que la carpeta del proyecto va fija (se escribe al compilar).
        string proyecto = @"__PROYECTO__";
        string script = Path.Combine(proyecto, "scripts", "iniciar.ps1");
        if (!File.Exists(script))
        {
            Console.WriteLine("No encuentro " + script);
            Console.WriteLine("Si moviste el proyecto, vuelve a ejecutar scripts\\crear-exe.ps1. Pulsa Enter.");
            Console.ReadLine();
            return 1;
        }
        IntPtr job = CrearJobQueMataAlCerrar(); // se mantiene abierto mientras viva este proceso
        var psi = new ProcessStartInfo("powershell.exe",
            "-NoProfile -ExecutionPolicy Bypass -File \"" + script + "\" " + string.Join(" ", args))
        { UseShellExecute = false };
        using (var p = Process.Start(psi))
        {
            // Los procesos que lance el script heredan el job (aun no habia creado ninguno).
            AssignProcessToJobObject(job, p.Handle);
            p.WaitForExit();
            return p.ExitCode;
        }
    }
}
