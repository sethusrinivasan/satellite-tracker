using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using SatTrack.Windows.Views;

namespace SatTrack.Windows;

public sealed partial class MainWindow : Window
{
    public MainWindow()
    {
        this.InitializeComponent();
        NavView.SelectedItem = NavView.MenuItems[0];
        ContentFrame.Navigate(typeof(TrackerPage));
    }

    private void NavView_SelectionChanged(NavigationView sender, NavigationViewSelectionChangedEventArgs args)
    {
        if (args.IsSettingsSelected)
        {
            ContentFrame.Navigate(typeof(SettingsPage));
            return;
        }

        if (args.SelectedItemContainer is NavigationViewItem item)
        {
            switch (item.Tag?.ToString())
            {
                case "Tracker":
                    ContentFrame.Navigate(typeof(TrackerPage));
                    break;
                case "Globe":
                    ContentFrame.Navigate(typeof(GlobePage));
                    break;
                case "Passes":
                    ContentFrame.Navigate(typeof(PassesPage));
                    break;
                case "Catalog":
                    ContentFrame.Navigate(typeof(CatalogPage));
                    break;
                case "Ai":
                    ContentFrame.Navigate(typeof(AiDiscoveryPage));
                    break;
            }
        }
    }
}
