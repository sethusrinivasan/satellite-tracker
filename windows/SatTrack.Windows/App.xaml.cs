using Microsoft.UI.Dispatching;
using Microsoft.UI.Xaml;

namespace SatTrack.Windows;

public partial class App : Application
{
    private Window? _window;
    public static DispatcherQueue? DispatcherQueue { get; private set; }

    public App()
    {
        this.InitializeComponent();
    }

    protected override void OnLaunched(LaunchActivatedEventArgs args)
    {
        _window = new MainWindow();
        DispatcherQueue = _window.DispatcherQueue;
        _window.Activate();
    }
}
