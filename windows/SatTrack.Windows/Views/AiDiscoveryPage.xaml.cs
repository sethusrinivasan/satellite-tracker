using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Input;
using SatTrack.Windows.Services;

namespace SatTrack.Windows.Views;

public sealed partial class AiDiscoveryPage : Page
{
    private readonly SatelliteRepository _repository = new();

    public AiDiscoveryPage()
    {
        this.InitializeComponent();
    }

    private void ExecuteQuery()
    {
        string prompt = TxtPrompt.Text?.Trim() ?? "";
        if (string.IsNullOrEmpty(prompt)) return;

        BtnSend.IsEnabled = false;
        var result = LocalQueryParser.ParseQuery(prompt, _repository.Satellites);
        TxtAiResponse.Text = result.Text;
        BtnSend.IsEnabled = true;
    }

    private void BtnSend_Click(object sender, RoutedEventArgs e) => ExecuteQuery();

    private void TxtPrompt_KeyDown(object sender, KeyRoutedEventArgs e)
    {
        if (e.Key == Windows.System.VirtualKey.Enter)
        {
            ExecuteQuery();
        }
    }
}
