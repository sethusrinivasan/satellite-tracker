import SwiftUI
import SceneKit

/// 3D Interactive SceneKit Globe view rendering real-time Earth, orbit ring, and satellite node.
public struct Globe3DView: View {
    @EnvironmentObject var viewModel: SatelliteViewModel

    public init() {}

    public var body: some View {
        ZStack {
            SceneKitView(state: viewModel.activeState)
                .edgesIgnoringSafeArea(.all)

            VStack {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("3D Orbital Space View")
                            .font(.headline)
                            .foregroundColor(.white)
                        if let state = viewModel.activeState {
                            Text("\(state.name) • \(Int(state.altKm)) km Alt")
                                .font(.caption)
                                .foregroundColor(Color(hex: state.colorHex))
                        }
                    }
                    .padding(12)
                    .background(.ultraThinMaterial)
                    .cornerRadius(12)

                    Spacer()
                }
                .padding(.horizontal)
                .padding(.top, 50)

                Spacer()
            }
        }
    }
}

private struct SceneKitView: UIViewRepresentable {
    let state: SatelliteState?

    func makeUIView(context: Context) -> SCNView {
        let scnView = SCNView()
        let scene = SCNScene()
        scnView.scene = scene
        scnView.allowsCameraControl = true
        scnView.autoenablesDefaultLighting = true
        scnView.backgroundColor = UIColor(red: 0.04, green: 0.06, blue: 0.10, alpha: 1.0)

        // Camera
        let cameraNode = SCNNode()
        cameraNode.camera = SCNCamera()
        cameraNode.position = SCNVector3(x: 0, y: 0, z: 5.0)
        scene.rootNode.addChildNode(cameraNode)

        // Earth Sphere
        let earthGeometry = SCNSphere(radius: 1.5)
        earthGeometry.firstMaterial?.diffuse.contents = UIColor(red: 0.12, green: 0.28, blue: 0.48, alpha: 1.0)
        earthGeometry.firstMaterial?.specular.contents = UIColor.white
        earthGeometry.firstMaterial?.shininess = 0.3
        let earthNode = SCNNode(geometry: earthGeometry)
        earthNode.name = "earthNode"
        scene.rootNode.addChildNode(earthNode)

        // Slow Earth Rotation Animation
        let rotateAction = SCNAction.rotateBy(x: 0, y: CGFloat(2.0 * .pi), z: 0, duration: 60)
        earthNode.runAction(SCNAction.repeatForever(rotateAction))

        // Satellite Marker Node
        let satGeometry = SCNSphere(radius: 0.08)
        satGeometry.firstMaterial?.diffuse.contents = UIColor(red: 0.22, green: 0.74, blue: 0.97, alpha: 1.0)
        let satNode = SCNNode(geometry: satGeometry)
        satNode.name = "satNode"
        satNode.position = SCNVector3(x: 1.9, y: 0, z: 0)
        scene.rootNode.addChildNode(satNode)

        return scnView
    }

    func updateUIView(_ uiView: SCNView, context: Context) {
        guard let state = state,
              let satNode = uiView.scene?.rootNode.childNode(withName: "satNode", recursively: false) else { return }

        // Convert lat, lng, alt to 3D Cartesian coordinates
        let latRad = Float(state.latDeg * .pi / 180.0)
        let lngRad = Float(state.lngDeg * .pi / 180.0)
        let r: Float = 1.5 + Float(state.altKm / 400.0) * 0.3

        let x = r * cos(latRad) * sin(lngRad)
        let y = r * sin(latRad)
        let z = r * cos(latRad) * cos(lngRad)

        SCNTransaction.begin()
        SCNTransaction.animationDuration = 0.5
        satNode.position = SCNVector3(x, y, z)
        SCNTransaction.commit()
    }
}
